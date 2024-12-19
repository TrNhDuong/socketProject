import socket
import time
import sys
import signal
import struct
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, messagebox, filedialog

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
BUFFER_SIZE = 1024  # 1KB
INPUT_FILE = "input.txt"
DOWNLOADED_FILE = "downloaded_files.txt"

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = (SERVER_HOST, SERVER_PORT)
# Hàm để in thông báo vào khung
def log_message(message):
    log_display.insert(tk.END, message + "\n")
    log_display.see(tk.END)  # Tự động cuộn xuống dòng cuối cùng

def receive_file_list(client_socket):
    file_list = []
    number_packet, server = client_socket.recvfrom(4)
    number_packet = struct.unpack('!I', number_packet)[0]
    received_data = [""]*number_packet
    for i in range(number_packet):
        data, server = client_socket.recvfrom(BUFFER_SIZE + 4)
        idx = data[0:4]
        idx = struct.unpack('!I', idx)[0]
        content = data[4:BUFFER_SIZE + 4]
        content = content.decode()
        received_data[idx] = content
        
    full_data = "".join(received_data)
    file_list = full_data.split(',')
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
        log_message(f"[!] Không tìm thấy file {INPUT_FILE}. Đảm bảo file tồn tại.")
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
        log_message(f"[!] Khong tim file {DOWNLOADED_FILE}")
        return []
    
def send_filename(filename):
    sizeName = struct.pack('!I', len(filename))
    client_socket.sendto(sizeName, server_address)
    client_socket.sendto(filename.encode(), server_address)    

def get_filename_filesize(file):
    filename, filesize = file.split('-')
    filename = filename[:-1]
    filesize = filesize[1:]
    size, byte = filesize.split(' ')
    return filename, int(size)
    
def count_sum(data):
    if len(data) % 2 != 0:
        data += b'\x00'
    
    checksum = 0
    for i in range(0, len(data), 2):
        # Ghép 2 byte thành một từ 16 bit
        word = (data[i] << 8) + data[i + 1]
        checksum += word
        # Thêm phần carry nếu vượt quá 16 bit
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    
    # Bù 1
    checksum = ~checksum & 0xFFFF
    return checksum

def receive_file(filename, size):
    total_received = 0
    log_message(f"Downloading file: {filename}")

    # Tạo file với kích thước cố định và mở nó
    with open(filename, "wb") as file_obj:
        file_obj.write(b'\x00' * size)
        file_obj.seek(0)

        # Tạo cửa sổ hiển thị tiến trình
        progress_window = tk.Toplevel(root)
        progress_window.title(f"Tiến trình tải {filename}")

        # Thanh tiến trình tổng
        total_progress = ttk.Progressbar(progress_window, orient="horizontal", length=400, mode="determinate")
        total_progress.pack(pady=10, padx=10)
        total_progress["maximum"] = size

        # Nhãn hiển thị phần trăm tổng
        total_label = tk.Label(progress_window, text="0%")
        total_label.pack()

        # Nhận dữ liệu
        while total_received < size:
            try:
                part, server = client_socket.recvfrom(BUFFER_SIZE + 4)
                checksum = part[0:4]
                checksum = struct.unpack('!I', checksum)[0]
                content = part[4:BUFFER_SIZE + 4]

                # Kiểm tra checksum
                cnt_sum = count_sum(content)
                if checksum == cnt_sum:
                    # Ghi dữ liệu vào file
                    file_obj.write(content)
                    total_received += len(content)

                    # Cập nhật giao diện
                    total_progress["value"] = total_received
                    percentage = int((total_received / size) * 100)
                    total_label.config(text=f"{percentage}%")
                    progress_window.update()

                    # Phản hồi tới server
                    client_socket.sendto("1".encode(), server_address)
                else:
                    client_socket.sendto("0".encode(), server_address)

            except Exception as e:
                log_message(f"Lỗi khi nhận dữ liệu: {e}")
                break

        time.sleep(2)
        # Đóng cửa sổ tiến trình
        progress_window.destroy()

    # Kiểm tra kết quả tải
    if total_received == size:
        log_message(f"Download completed: {filename}")
        with open(DOWNLOADED_FILE, "a") as file_obj:
            file_obj.write(filename + '\n')
    else:
        log_message(f"Download incomplete: Received {total_received}/{size} bytes")

def handle():
    client_socket.sendto(b"0", server_address)
    messagebox.showinfo("Thông báo", "Đã kết nối tới server!")
    file_list = receive_file_list(client_socket)
    display = receive_file_list(client_socket)
    list_namefile = []
    list_sizefile = []
    log_message("Danh sách các file có thể download từ server:")
    for file in display:
        log_message(file)
        
    for file in file_list:
        name, size = get_filename_filesize(file)
        list_namefile.append(name)
        list_sizefile.append(size)

    downloaded_file =[]
    checked_file = []
    log_message("Nhập vào file Input")
    while True:
        downloaded_file = get_downloaded_file()
        input_file = get_files_to_download()
        if input_file != []:
            for file in input_file:
                if file not in checked_file:
                    if file in list_namefile and file not in downloaded_file:
                        i = list_namefile.index(file)
                        send_filename(file)
                        size = list_sizefile[i]
                        receive_file(file, size)
                    elif file not in list_namefile:
                        log_message(f"[!] File {file} không tồn tại")
                    elif file in downloaded_file:
                        log_message(f"[!] File {file} đã tải xuống")
                    checked_file.append(file)
        time.sleep(5)
        log_message("Dang quet file input")

def handle_exit(signal_received, frame):
    log_message("\n[!] Ctrl + C được nhấn. Đang đóng kết nối...")
    if client_socket:
        try:
            client_socket.close()  # Đóng socket nếu đang kết nối
            log_message("[+] Kết nối đã được đóng.")
        except Exception as e:
            log_message(f"[!] Lỗi khi đóng socket: {e}")
    sys.exit(0)  # Thoát chương trình

# Hàm chạy chương trình trong luồng riêng
def start_program():
    start_button.config(state="disabled")
    threading.Thread(target=handle, daemon=True).start()


# Gắn xử lý tín hiệu Ctrl + C
signal.signal(signal.SIGINT, handle_exit) 

# Tạo cửa sổ chính
root = tk.Tk()
root.title("UDP Client")

# Tạo một khung có thanh cuộn
log_display = ScrolledText(root, width=60, height=20, wrap=tk.WORD)
log_display.pack(padx=10, pady=10)

# Tạo nút để bắt đầu chương trình
start_button = tk.Button(root, text="Chạy chương trình", command=start_program)
start_button.pack(pady=10)

# Bắt đầu vòng lặp giao diện
root.mainloop()
