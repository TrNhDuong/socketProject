import socket
import os
import threading
import struct
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# Server configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5001
BUFFER_SIZE = 1024  # 1KB
FILE_DIRECTORY = "fordown"  # Thư mục chứa các file

# Mảng chứa các địa chỉ đã kết nối
connected_addr = []
file_list = []

# Tạo giao diện hiển thị thông báo server
root = tk.Tk()
root.title("TCP Server")
root.geometry("600x400")

# Khung hiển thị log
log_frame = tk.Frame(root)
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

log_text = ScrolledText(log_frame, state='disabled', height=20, wrap=tk.WORD)
log_text.pack(fill=tk.BOTH, expand=True)

# Hàm thêm log vào giao diện
def log_message(message):
    log_text.configure(state='normal')
    log_text.insert(tk.END, f"{message}\n")
    log_text.configure(state='disabled')
    log_text.yview(tk.END)

# Hàm lấy danh sách các file có thể tải được
def get_file_list():
    file_list = []
    if os.path.exists(FILE_DIRECTORY):
        for filename in os.listdir(FILE_DIRECTORY):
            file_path = os.path.join(FILE_DIRECTORY, filename)
            if os.path.isfile(file_path):
                filesize = os.path.getsize(file_path)
                file_list.append(f"{filename} - {filesize} byte")
    return file_list

def read_contain_file():
    with open("listfile.txt", "r") as file_obj:
        lines = []
        for line in file_obj.readlines():
            if line.strip():
                lines.append(line.strip())
    return lines

def send_file_list(client_socket, file_list):
    # Chuyển mảng thành chuỗi ngăn cách bởi dấu ',' giữa các filefile
    data = ','.join(file_list)
    data_length = len(data)
    packed_length = struct.pack('!I', data_length)
    client_socket.send(packed_length)
    client_socket.sendall(data.encode())


def send_chunk(client_socket, filename, start, end):
    with open(FILE_DIRECTORY + "\\" + filename, "rb") as file_obj:
        file_obj.seek(start)
        total_sent = 0
        while total_sent < (end - start):
            bytes_to_send = file_obj.read(BUFFER_SIZE)
            if not bytes_to_send:
                break
            client_socket.sendall(bytes_to_send)
            total_sent += len(bytes_to_send)
    file_obj.close()


def handle_client(client_socket, address):
    if address not in connected_addr:
        connected_addr.append(address)
    log_message(f"[+] Nhận được kết nối từ {client_socket.getpeername()}")
    
    display = read_contain_file()
    file_list = get_file_list()
    send_file_list(client_socket, file_list)
    log_message(f"Đã gửi danh sách file cho {client_socket.getpeername()}")
    send_file_list(client_socket, display)
    message = client_socket.recv(5).decode()
    if message == "close":
        log_message(f"[+] Client {address} đã ngắt kết nối")


def connect_from_client(client_socket, address):
    signal = client_socket.recv(1).decode('utf-8')
    if signal == "0":
        handle_client(client_socket, address)
    else:
        lenStr = client_socket.recv(4)
        lenStr = struct.unpack('!I', lenStr)[0]
        mess = client_socket.recv(lenStr).decode()
        filename, start, end = mess.split(',')
        start, end = int(start), int(end)
        send_chunk(client_socket, filename, start, end)
    client_socket.close()

# Vòng lặp chính của server trên luồng phụ
def start_server():
    display = read_contain_file()
    log_message("Các file có thể download trên Server:")
    for file in display:
        log_message(file)
    log_message(f"[*] Đang lắng nghe tại {SERVER_HOST}:{SERVER_PORT}")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)

    while True:
        client_socket, address = server_socket.accept()
        client = threading.Thread(target=connect_from_client, args=(client_socket, address))
        client.start()

# Chạy server trên một luồng riêng
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# Chạy giao diện trên luồng chính
root.mainloop()
