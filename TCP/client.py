import socket
import tqdm
import time
import threading
import signal
import sys
import struct

# Client configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
BUFFER_SIZE = 1024
INPUT_FILE = "input.txt"  # File chứa danh sách các file cần tải
DOWNLOADED_FILE = "downloaded_files.txt"

stop = threading.Event()
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
display_list = []

def receive_file_list(client_socket):
    # Nhận độ dài chuỗi 
    data_length = client_socket.recv(4)
    data_length = struct.unpack('!I', data_length)[0]
    # Nhận chuỗi 
    data = client_socket.recv(data_length).decode()
    # Chuyển chuỗi thành danh sách
    file_list = data.split(',') if data else []
    return file_list

def get_files_to_download():
    try:
        with open(INPUT_FILE, "r") as file:
            files = []
            for line in file.readlines():
                if line.strip():
                    files.append(line.strip()) 
        return files
    except FileNotFoundError:
        print(f"[!] Không tìm thấy file {INPUT_FILE}. Đảm bảo file tồn tại.")
        return []

def get_downloaded_file():
    try:
        with open(DOWNLOADED_FILE, "r") as file:
            files = []
            for line in file.readlines():
                if line.strip():
                    files.append(line.strip())
            return files
    except FileNotFoundError:
        print(f"[!] Khong tim file {DOWNLOADED_FILE}")
        return []
    

def display_percent_download(progress):   
    while not stop.is_set():
            progress_status = " | ".join([f"Part {i+1}: {p:.2f}%" for i, p in enumerate(progress)])
            print(f"\r{progress_status}", end="")

            if all(p >= 100 for p in progress):
                break
    print("\r" + " | ".join([f"Part {i+1}: {100:.2f}%" for i, p in enumerate(progress)]), end = "")
    print()
    print(f"\rDownload completed", end="\n")
    print()
    
def receive_chunk(filename, start_end, progress, i):
    start, end = start_end
    part_connect = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    part_connect.connect((SERVER_HOST, SERVER_PORT))
    # Gửi signal kiểm tra là tải chunk hay là kết nối mới
    part_connect.send("1".encode('utf-8'))

    # Gửi tên file muốn download, vị trí bắt đầu tải và dừng
    send_str = filename + ',' + f"{start},{end}"
    packet = struct.pack('!I', len(send_str))
    part_connect.send(packet)
    part_connect.sendall(send_str.encode())

    # Nhận data từ server và tải dữ liệu về
    total_bytes = end - start
    total_received = 0
    if total_bytes > 0:
        with open(filename, "r+b") as file_obj:
            file_obj.seek(start)
            while total_received < total_bytes:
                bytes_read = part_connect.recv(min(BUFFER_SIZE, total_bytes - total_received))
                if not bytes_read:
                    break
                file_obj.write(bytes_read)
                total_received += len(bytes_read)
                progress[i] = total_received/total_bytes*100
    part_connect.close()


# Hàm tải file về Client 
def receive_file(client_socket, filename, filesize):
    print(f"Receiving {filename}...")
    unit = int(filesize/4)
    length_of_chunk = [
        (0, unit),
        (unit, 2 * unit),
        (2 * unit, 3 * unit),
        (3 * unit, filesize)
    ]
    threads = []
    progress = [0] * 4

    with open(filename, "wb") as file_obj:
        file_obj.write(b'\x00' * filesize)

    with open(DOWNLOADED_FILE, 'a') as file_obj:
        file_obj. write(filename + "\n")
    
    for i in range(len(length_of_chunk)):
        thread = threading.Thread(target=receive_chunk, args=(filename, length_of_chunk[i], progress, i))
        threads.append(thread)
    
    for thread in threads:
        thread.start()
    
    display_percent_download(progress)

    for thread in threads:
        thread.join()

def get_filename_filesize(file):
    filename, filesize = file.split(" - ")
    filesize, bytes = filesize.split(' ')
    return filename, int(filesize)

# Hàm kết nối tới Server
def connect_to_server():
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    print(f"[+] Đã kết nối đến Server {SERVER_PORT}")
    client_socket.send("0".encode())
    # Nhận danh sách các file có thể download
    file_list = receive_file_list(client_socket)
    # Nhận danh sách hiển thịthị
    display_list = receive_file_list(client_socket)
    filename_list = []
    filesize_list = []
    # Hiển thị danh sáchsách
    print(f"Danh sách file có thể download từ Server: ")
    for file in display_list:
        print(file)

    for file in file_list:
        name, size = get_filename_filesize(file)
        filename_list.append(name)
        filesize_list.append(size)

    
    # Nhập danh sách các file muốn download
    print("Nhập danh sách file muốn download vào file input.txt")
    input_file = []
    # Nhận và tải các file
    checked_file = []
    downloaded_file = []
    while True:
        print("Đang quét file input")
        input_file = get_files_to_download()
        downloaded_file = get_downloaded_file()
        for file in input_file:
            if file not in checked_file:
                if file in filename_list and file not in downloaded_file:
                    i = filename_list.index(file)
                    size = filesize_list[i]
                    receive_file(client_socket, file, size)
                elif file not in filename_list:
                    print(f"[!] File {file} không tồn tại")
                elif file in downloaded_file:
                    print(f"[!] File {file} đã được tải")
                checked_file.append(file)
        time.sleep(5)

# Hàm xử lí Ctrl + C
def handle_exit(signal_received, frame):
    print("\n[!] Ctrl + C được nhấn. Đang đóng kết nối...")
    client_socket.send("close".encode())
    if client_socket:
        try:
            client_socket.close()  # Đóng socket nếu đang kết nối
            print("[+] Kết nối đã được đóng.")
        except Exception as e:
            print(f"[!] Lỗi khi đóng socket: {e}")
    sys.exit(0)  # Thoát chương trình

# Gắn xử lý tín hiệu Ctrl + C
signal.signal(signal.SIGINT, handle_exit)               

# Bắt đầu kết nối và tải file
if __name__ == "__main__":
    connect_to_server()