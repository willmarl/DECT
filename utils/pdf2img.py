"""
The reason why transforming PDF to images is to get higher accuracy in text extraction.
When sending to LLM, images yield better results than raw PDFs.
"""
from pdf2image import convert_from_bytes, convert_from_path
from pathlib import Path
import os

input_folder_name = "inputs"

def fresh_pdf_folders():
    p = Path(input_folder_name)
    if p.exists():
        for folder in p.iterdir():
            for file in folder.iterdir():
                file.unlink()
            folder.rmdir()
    else:
        p.mkdir()

def make_folder(folder_name):
    p = Path(f"{input_folder_name}/{folder_name}")
    p.mkdir()

def pdf_to_images(pdf_bytes):
    """
    this is very inefficient as any file upload or remove will restart the whole process
    will optimize later
    """
    fresh_pdf_folders() # clear old folders
    fileList = []
    # get list of filenames
    for file in pdf_bytes:
        fileList.append(os.path.splitext(os.path.basename(file.name))[0])

    # save images to respective folders
    for i, fileName in enumerate(fileList):
        make_folder(fileName)
        # read the actual file content from the Gradio file object
        with open(pdf_bytes[i].name, 'rb') as file:
            file_bytes = file.read()
        images = convert_from_bytes(file_bytes, dpi=300)
        for j, img in enumerate(images):
            img.save(f"{input_folder_name}/{fileName}/{j+1}.png", "PNG")

    if len(fileList) > 0:
        from utils.extractFR import extractFRfromImage
        extractFRfromImage()
        return True
    else:
        return False