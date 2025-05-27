import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import override_settings
from pathlib import Path
import os
import datetime
import shutil
import json # For loading response.content if it's JSON

# Helper function to get a file from test_data
def get_test_file(test_data_path, filename, content_type):
    file_path = test_data_path / filename
    assert file_path.exists(), f"Test file {filename} not found in {test_data_path}"
    return SimpleUploadedFile(file_path.name, file_path.read_bytes(), content_type=content_type)

# === Test Cases for ImgToFile ===

@pytest.mark.django_db
def test_img_to_word_single_no_merge(authenticated_client, test_data_path, temp_media_root):
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        image_file = get_test_file(test_data_path, "test_1.jpg", "image/jpeg")
        
        data = {
            "main_tab": "imgToFile",
            "sub_tab": "imgToWord",
            "merge_output": "false",
            "output_format": "docx",
            "images": [image_file]
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        
        assert response_data["merge_output"] == False
        assert len(response_data["results"]) == 1
        result = response_data["results"][0]
        assert result["status"] == "success"
        assert result["original_name"] == "test_1.jpg"
        assert result["converted_name"].endswith(".docx")
        assert "download_url" in result

        # Check if the file was created in the temp_media_root structure
        # user = 'testuser', date = today_date_str
        today_date_str = datetime.datetime.now().strftime("%Y%m%d")
        expected_dir = temp_media_root["HIS_PIC_TEMP_BASE"] / 'his_pic' / 'testuser' / today_date_str / 'converted_files'
        assert expected_dir.exists()
        created_files = list(expected_dir.glob("*.docx"))
        assert len(created_files) == 1
        assert created_files[0].name == result["converted_name"]
        # Optionally copy to test_output for inspection
        # shutil.copy(created_files[0], temp_media_root["TEST_SPECIFIC_OUTPUT"])

@pytest.mark.django_db
def test_imgs_to_pdf_multiple_no_merge(authenticated_client, test_data_path, temp_media_root):
    # Renamed to reflect multiple images, no merge
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        
        image_files = []
        expected_original_names = []
        for i in range(1, 7): # test_1.jpg to test_6.jpg
            filename = f"test_{i}.jpg"
            image_files.append(get_test_file(test_data_path, filename, "image/jpeg"))
            expected_original_names.append(filename)

        data = {
            "main_tab": "imgToFile",
            "sub_tab": "imgToPdf",
            "merge_output": "false", # Key: No merge
            "output_format": "pdf",
            "images": image_files
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        
        assert not response_data["merge_output"]
        assert len(response_data["results"]) == 6 # Expect 6 individual results
        
        converted_original_names = sorted([res["original_name"] for res in response_data["results"]])
        assert sorted(expected_original_names) == converted_original_names

        for result in response_data["results"]:
            assert result["status"] == "success" # or success_with_issue for individual files
            assert result["original_name"] in expected_original_names
            assert result["converted_name"].endswith(".pdf")
            assert "download_url" in result

@pytest.mark.django_db
def test_imgs_to_word_multiple_merge(authenticated_client, test_data_path, temp_media_root):
    # Renamed to reflect multiple images
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        
        image_files = []
        expected_original_names_in_merged_result = []
        for i in range(1, 7): # test_1.jpg to test_6.jpg
            filename = f"test_{i}.jpg"
            image_files.append(get_test_file(test_data_path, filename, "image/jpeg"))
            expected_original_names_in_merged_result.append(filename)
        
        data = {
            "main_tab": "imgToFile",
            "sub_tab": "imgToWord",
            "merge_output": "true", # Key: Merge
            "output_format": "docx",
            "images": image_files
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        
        assert response_data["merge_output"]
        assert len(response_data["results"]) == 1 # Expect 1 merged result
        
        result = response_data["results"][0]
        assert result["status"] == "success"
        # The original_name field for merged results should be a comma-separated list
        for name_part in expected_original_names_in_merged_result:
            assert name_part in result["original_name"].split(',')
        assert result["converted_name"].endswith(".docx")
        assert "download_url" in result

# === Test Cases for FileToPdf ===

@pytest.mark.django_db
def test_word_to_pdf_single_no_merge(authenticated_client, test_data_path, temp_media_root):
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        word_file = get_test_file(test_data_path, "test_word.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        data = {
            "main_tab": "fileToPdf",
            "sub_tab": "wordToPdf",
            "merge_output": "false",
            # output_format is implicitly pdf for fileToPdf
            "images": [word_file] # Key is still 'images' in the view
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert not response_data["merge_output"]
        assert len(response_data["results"]) == 1
        result = response_data["results"][0]
        assert result["status"] == "success"
        assert result["original_name"] == "test_word.docx"
        assert result["converted_name"].endswith(".pdf")

@pytest.mark.django_db
def test_excel_to_pdf_multiple_merge(authenticated_client, test_data_path, temp_media_root):
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        excel1 = get_test_file(test_data_path, "test_excel.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        # Add another excel file if you have one for merging, e.g., test_excel_2.xlsx
        # excel2 = get_test_file(test_data_path, "test_excel_2.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        data = {
            "main_tab": "fileToPdf",
            "sub_tab": "excelToPdf",
            "merge_output": "true",
            "images": [excel1] #, excel2]
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["merge_output"]
        assert len(response_data["results"]) == 1
        result = response_data["results"][0]
        assert result["status"] == "success"
        assert "test_excel.xlsx" in result["original_name"]
        assert result["converted_name"].endswith(".pdf")

# === Test Cases for PdfToFile ===

@pytest.mark.django_db
def test_pdf_to_word_single_no_merge(authenticated_client, test_data_path, temp_media_root):
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        pdf_file = get_test_file(test_data_path, "test_word.pdf", "application/pdf")
        data = {
            "main_tab": "pdfToFile",
            "sub_tab": "pdfToWord",
            "merge_output": "false",
            "output_format": "docx",
            "images": [pdf_file]
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert not response_data["merge_output"]
        assert len(response_data["results"]) == 1
        result = response_data["results"][0]
        assert result["status"] == "success"
        assert result["original_name"] == "test_word.pdf"
        assert result["converted_name"].endswith(".docx")

@pytest.mark.django_db
def test_pdf_to_txt_multiple_merge(authenticated_client, test_data_path, temp_media_root):
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        pdf1 = get_test_file(test_data_path, "test_txt.pdf", "application/pdf")
        # Add another pdf file if you have one for merging, e.g., test_another_for_txt.pdf
        # pdf2 = get_test_file(test_data_path, "test_another_for_txt.pdf", "application/pdf")
        data = {
            "main_tab": "pdfToFile",
            "sub_tab": "pdfToTxt",
            "merge_output": "true",
            "output_format": "txt",
            "images": [pdf1] #, pdf2]
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["merge_output"]
        assert len(response_data["results"]) == 1
        result = response_data["results"][0]
        assert result["status"] == "success"
        assert "test_txt.pdf" in result["original_name"]
        assert result["converted_name"].endswith(".txt")

# === Placeholder for Error Handling Tests ===
@pytest.mark.django_db
def test_unsupported_file_type_for_conversion(authenticated_client, test_data_path, temp_media_root):
    with override_settings(BASE_DIR=temp_media_root["HIS_PIC_TEMP_BASE"].parent):
        url = reverse("converter:process_images")
        # Example: Trying to convert a .zip file when fileToPdf -> wordToPdf is selected
        # This specific scenario might be caught by frontend accept types, but backend should also handle.
        # The view logic currently copies based on extension, then converter fails or view has specific check.
        # Let's try sending a .txt to wordToPdf which should be an invalid type for that sub_tab.
        txt_file = get_test_file(test_data_path, "test_txt.txt", "text/plain")
        data = {
            "main_tab": "fileToPdf",
            "sub_tab": "wordToPdf", # Expects .doc/.docx
            "merge_output": "false",
            "images": [txt_file]
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200 # View might still return 200 but with error status in JSON
        response_data = json.loads(response.content)
        assert len(response_data["results"]) == 1
        result = response_data["results"][0]
        assert result["status"] == "error"
        assert "文件类型不匹配" in result.get("message", "") # Check for expected error message 