import os
import shutil

base_path = r'C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\assistente Atena'
src_path = os.path.join(base_path, 'src')

# Mover arquivos .py do diretório base para src
for item in os.listdir(base_path):
    if item.endswith('.py'):
        src_file_path = os.path.join(base_path, item)
        dest_file_path = os.path.join(src_path, item)
        shutil.move(src_file_path, dest_file_path)
        print(f'Moved .py file: {src_file_path} to {dest_file_path}')

# Mover o conteúdo de _legado para src
legado_path = os.path.join(base_path, '_legado')
if os.path.exists(legado_path):
    for item in os.listdir(legado_path):
        s = os.path.join(legado_path, item)
        d = os.path.join(src_path, item)
        if os.path.isdir(s):
            shutil.move(s, d)
            print(f'Moved directory from _legado: {s} to {d}')
        else:
            shutil.move(s, d)
            print(f'Moved file from _legado: {s} to {d}')
    os.rmdir(legado_path)
    print(f'Removed directory: {legado_path}')

# Mover o conteúdo de backend/app para src
backend_app_path = os.path.join(base_path, 'backend', 'app')
if os.path.exists(backend_app_path):
    for item in os.listdir(backend_app_path):
        s = os.path.join(backend_app_path, item)
        d = os.path.join(src_path, item)
        if os.path.isdir(s):
            shutil.move(s, d)
            print(f'Moved directory from backend/app: {s} to {d}')
        else:
            shutil.move(s, d)
            print(f'Moved file from backend/app: {s} to {d}')

# Mover arquivos .py de backend para src (se houver)
backend_path = os.path.join(base_path, 'backend')
if os.path.exists(backend_path):
    for item in os.listdir(backend_path):
        if item.endswith('.py'):
            src_file_path = os.path.join(backend_path, item)
            dest_file_path = os.path.join(src_path, item)
            shutil.move(src_file_path, dest_file_path)
            print(f'Moved .py file from backend: {src_file_path} to {dest_file_path}')

# Mover o requirements.txt de backend para a raiz
backend_requirements = os.path.join(base_path, 'backend', 'requirements.txt')
if os.path.exists(backend_requirements):
    shutil.move(backend_requirements, os.path.join(base_path, 'requirements.txt'))
    print(f'Moved requirements.txt from backend to root.')

# Remover a pasta backend vazia (se estiver vazia)
if os.path.exists(backend_path) and not os.listdir(backend_path):
    os.rmdir(backend_path)
    print(f'Removed empty directory: {backend_path}')