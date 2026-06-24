#!/usr/bin/env python3
"""
Koldi CRDTs — Estado concorrente sem lock usando Vector Clocks e LWW-Register.
Implementação Python dos primitivos CRDT para sincronização entre instâncias.

Baseado em: CodeCRDT (arXiv:2510.18893) — 100% convergência, zero merge failures.
"""

import json
import time
import hashlib
from datetime import datetime
from typing import Any, Dict, Optional


class VectorClock:
    """Vector Clock para ordenação causal."""
    
    def __init__(self, clock: Dict[str, int] = None):
        self.clock = clock or {}
    
    def increment(self, node_id: str):
        self.clock[node_id] = self.clock.get(node_id, 0) + 1
    
    def merge(self, other: 'VectorClock'):
        for node, ts in other.clock.items():
            self.clock[node] = max(self.clock.get(node, 0), ts)
    
    def compare(self, other: 'VectorClock') -> Optional[str]:
        """Retorna 'before', 'after', 'concurrent', ou 'equal'."""
        dominates = False
        dominated = False
        
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for node in all_nodes:
            a = self.clock.get(node, 0)
            b = other.clock.get(node, 0)
            if a > b:
                dominates = True
            elif b > a:
                dominated = True
        
        if dominates and not dominated:
            return 'after'
        elif dominated and not dominates:
            return 'before'
        elif not dominates and not dominated:
            return 'equal'
        else:
            return 'concurrent'
    
    def to_dict(self):
        return dict(self.clock)
    
    @classmethod
    def from_dict(cls, d):
        return cls(dict(d))


class LWWRegister:
    """Last-Write-Wins Register — resolve conflitos pelo timestamp."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.value = None
        self.timestamp = 0
        self.vector_clock = VectorClock()
    
    def set(self, value: Any):
        self.value = value
        self.timestamp = time.time()
        self.vector_clock.increment(self.node_id)
    
    def merge(self, other: 'LWWRegister'):
        cmp = self.vector_clock.compare(other.vector_clock)
        if cmp == 'before' or (cmp == 'concurrent' and other.timestamp > self.timestamp):
            self.value = other.value
            self.timestamp = other.timestamp
            self.vector_clock.merge(other.vector_clock)
            return True
        return False
    
    def to_dict(self):
        return {
            'value': self.value,
            'timestamp': self.timestamp,
            'vector_clock': self.vector_clock.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, d, node_id: str):
        reg = cls(node_id)
        reg.value = d.get('value')
        reg.timestamp = d.get('timestamp', 0)
        reg.vector_clock = VectorClock.from_dict(d.get('vector_clock', {}))
        return reg


class ORSet:
    """Observed-Remove Set — add wins sobre remove."""
    
    def __init__(self):
        self.adds: Dict[str, set] = {}  # element -> set of unique tags
        self.removes: Dict[str, set] = {}  # element -> set of unique tags
    
    def add(self, element: str, tag: str = None):
        tag = tag or self._gen_tag()
        if element not in self.adds:
            self.adds[element] = set()
        self.adds[element].add(tag)
    
    def remove(self, element: str):
        if element in self.adds:
            self.removes[element] = set(self.adds[element])
    
    def contains(self, element: str) -> bool:
        adds = self.adds.get(element, set())
        removes = self.removes.get(element, set())
        return bool(adds - removes)
    
    def elements(self) -> set:
        result = set()
        for elem in self.adds:
            if self.contains(elem):
                result.add(elem)
        return result
    
    def merge(self, other: 'ORSet'):
        for elem, tags in other.adds.items():
            if elem not in self.adds:
                self.adds[elem] = set()
            self.adds[elem] |= tags
        for elem, tags in other.removes.items():
            if elem not in self.removes:
                self.removes[elem] = set()
            self.removes[elem] |= tags
    
    def _gen_tag(self):
        return hashlib.md5(f"{time.time()}-{id(self)}".encode()).hexdigest()[:8]
    
    def to_dict(self):
        return {
            'adds': {k: list(v) for k, v in self.adds.items()},
            'removes': {k: list(v) for k, v in self.removes.items()},
        }
    
    @classmethod
    def from_dict(cls, d):
        s = cls()
        s.adds = {k: set(v) for k, v in d.get('adds', {}).items()}
        s.removes = {k: set(v) for k, v in d.get('removes', {}).items()}
        return s


class StateMerge:
    """Merge de estado completo entre duas instâncias."""
    
    @staticmethod
    def merge_states(local: Dict, remote: Dict, node_id: str) -> Dict:
        """Merge dois estados, resolvendo conflitos com LWW."""
        result = {}
        all_keys = set(local.keys()) | set(remote.keys())
        
        for key in all_keys:
            if key not in local:
                result[key] = remote[key]
            elif key not in remote:
                result[key] = local[key]
            else:
                # Conflito — usar LWW
                local_ts = local[key].get('timestamp', 0) if isinstance(local[key], dict) else 0
                remote_ts = remote[key].get('timestamp', 0) if isinstance(remote[key], dict) else 0
                result[key] = remote[key] if remote_ts > local_ts else local[key]
        
        return result


class KoldiCRDT:
    """Gerenciador CRDT para o Koldi — sincroniza estado entre local e nuvem."""
    
    def __init__(self, node_id: str, state_file: str = None):
        self.node_id = node_id
        self.state_file = state_file or f"/opt/hermes/crdt_state_{node_id}.json"
        self.registers: Dict[str, LWWRegister] = {}
        self.sets: Dict[str, ORSet] = {}
        self.metadata: Dict[str, Any] = {}
        self._load()
    
    def set(self, key: str, value: Any):
        if key not in self.registers:
            self.registers[key] = LWWRegister(self.node_id)
        self.registers[key].set(value)
        self._save()
    
    def get(self, key: str) -> Any:
        reg = self.registers.get(key)
        return reg.value if reg else None
    
    def add_to_set(self, set_name: str, element: str):
        if set_name not in self.sets:
            self.sets[set_name] = ORSet()
        self.sets[set_name].add(element)
        self._save()
    
    def remove_from_set(self, set_name: str, element: str):
        if set_name in self.sets:
            self.sets[set_name].remove(element)
            self._save()
    
    def get_set(self, set_name: str) -> set:
        s = self.sets.get(set_name)
        return s.elements() if s else set()
    
    def merge(self, remote_state: Dict):
        """Merge estado remoto."""
        for key, reg_data in remote_state.get('registers', {}).items():
            remote_reg = LWWRegister.from_dict(reg_data, self.node_id)
            if key not in self.registers:
                self.registers[key] = remote_reg
            else:
                self.registers[key].merge(remote_reg)
        
        for key, set_data in remote_state.get('sets', {}).items():
            remote_set = ORSet.from_dict(set_data)
            if key not in self.sets:
                self.sets[key] = remote_set
            else:
                self.sets[key].merge(remote_set)
        
        self._save()
    
    def export_state(self) -> Dict:
        """Exporta estado para sync."""
        return {
            'node_id': self.node_id,
            'timestamp': time.time(),
            'registers': {k: v.to_dict() for k, v in self.registers.items()},
            'sets': {k: v.to_dict() for k, v in self.sets.items()},
            'metadata': self.metadata,
        }
    
    def _save(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.export_state(), f, indent=2, default=str)
        except Exception:
            pass
    
    def _load(self):
        try:
            if __import__('os').path.exists(self.state_file):
                with open(self.state_file) as f:
                    data = json.load(f)
                for k, v in data.get('registers', {}).items():
                    self.registers[k] = LWWRegister.from_dict(v, self.node_id)
                for k, v in data.get('sets', {}).items():
                    self.sets[k] = ORSet.from_dict(v)
                self.metadata = data.get('metadata', {})
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    
    args = sys.argv[1:]
    if not args:
        print("Uso: python crdt_sync.py <set|get|add|remove|export|import|merge|stats> [args]")
        sys.exit(1)
    
    cmd = args[0]
    node_id = "local"
    
    # Se o primeiro arg é --node, usar como node_id
    if cmd == "--node" and len(args) >= 2:
        node_id = args[1]
        args = args[2:]
        if not args:
            print("Comando faltando")
            sys.exit(1)
        cmd = args[0]
    
    crdt = KoldiCRDT(node_id)
    
    if cmd == "set" and len(args) >= 3:
        key, value = args[1], args[2]
        crdt.set(key, value)
        print(f"  {key} = {value}")
    
    elif cmd == "get" and len(args) >= 2:
        value = crdt.get(args[1])
        print(f"  {args[1]} = {value}")
    
    elif cmd == "add" and len(args) >= 3:
        crdt.add_to_set(args[1], args[2])
        print(f"  + {args[2]} -> {args[1]}")
    
    elif cmd == "remove" and len(args) >= 3:
        crdt.remove_from_set(args[1], args[2])
        print(f"  - {args[2]} <- {args[1]}")
    
    elif cmd == "export":
        print(json.dumps(crdt.export_state(), indent=2, default=str))
    
    elif cmd == "import" and len(args) >= 2:
        with open(args[1]) as f:
            crdt.merge(json.load(f))
        print("Estado importado")
    
    elif cmd == "merge" and len(args) >= 2:
        with open(args[1]) as f:
            crdt.merge(json.load(f))
        print("Merge completo")
    
    elif cmd == "stats":
        state = crdt.export_state()
        print(f"Registros: {len(state['registers'])}")
        print(f"Sets: {len(state['sets'])}")
        for k, v in state['registers'].items():
            print(f"  {k} = {v['value']} (ts: {v['timestamp']:.0f})")
    
    else:
        print(f"Comando desconhecido ou argumentos insuficientes: {cmd}")
