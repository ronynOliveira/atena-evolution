import ctypes

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
    ]

stat = MEMORYSTATUSEX()
stat.dwLength = ctypes.sizeof(stat)
ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

total_gb = stat.ullTotalPhys / (1024**3)
avail_gb = stat.ullAvailPhys / (1024**3)
used_gb = total_gb - avail_gb
pct = stat.dwMemoryLoad

print(f"RAM: {used_gb:.1f} GB usado / {total_gb:.1f} GB total ({pct}%) | Livre: {avail_gb:.1f} GB")

print("\n=== RAM POR MODELO (estimativa) ===")
modelos_ram = {
    "gemma4:e2b (5.1B Q4_K_M)": 4.5,
    "gemma4:e4b (8B Q4_K_M)": 7.0,
    "hermes3:8b (8B Q4_0)": 6.0,
    "phi4-mini (3.8B Q4_K_M)": 3.5,
    "nomic-embed-text (137M)": 0.3,
}
for modelo, ram in modelos_ram.items():
    status = "OK" if ram < avail_gb else "PESADO"
    print(f"  {modelo:35s} ~{ram:.1f}GB  [{status}]")

print(f"\nCom {avail_gb:.1f}GB livre:")
print(f"  Opcao A: 1 modelo medio (4.5GB) + nomic-embed (0.3GB) + cache KV")
print(f"  Opcao B: 2 modelos pequenos (3.5GB cada) alternando")
print(f"  Opcao C: 1 modelo grande (6-7GB) + RAG local")
