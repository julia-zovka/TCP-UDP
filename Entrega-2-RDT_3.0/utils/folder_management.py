import os
import shutil

def delete_folder(base_path: str, nickname: str) -> None:
   ## Remove tudo que estiver em base_path/nickname e recria a pasta vazia.
    folder = os.path.join(base_path, nickname)
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder, exist_ok=True)
