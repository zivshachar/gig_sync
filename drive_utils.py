
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import os
import io

def build_drive_service(credentials):
    return build("drive", "v3", credentials=credentials)

def upload_file(service, file_path, file_name=None, mime_type="application/octet-stream", parent_folder_id=None):
    file_metadata = {
        "name": file_name or os.path.basename(file_path)
    }
    if parent_folder_id:
        file_metadata["parents"] = [parent_folder_id]

    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink"
    ).execute()
    return file

def list_drive_files(service, folder_id=None, mime_type=None, limit=10):
    query_parts = []
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")
    if mime_type:
        query_parts.append(f"mimeType = '{mime_type}'")
    query = " and ".join(query_parts)

    results = service.files().list(
        q=query or None,
        pageSize=limit,
        fields="files(id, name, mimeType, webViewLink)"
    ).execute()
    return results.get("files", [])

def delete_file(service, file_id):
    service.files().delete(fileId=file_id).execute()
    return True

def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return dest_path

def export_google_doc(service, file_id, export_mime_type="application/pdf", dest_path=None):
    request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    if dest_path:
        with open(dest_path, "wb") as f:
            f.write(fh.getvalue())
        return dest_path
    else:
        return fh.getvalue()
