import socket
import struct
import time
import threading
import signal
import sys
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, messagebox, filedialog

# Client configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
BUFFER_SIZE = 1024
INPUT_FILE = "input.txt"  # File chứa danh sách các file cần tải
DOWNLOADED_FILE = "downloaded_files.txt"

client_socket = socket.socket()
# Hàm để in thông báo vào khung
def log_message(message):
    log_display.insert(tk.END, message + "\n")
    log_display.see(tk.END)  # Tự động cuộn xuống dòng cuối cùng

# Hàm nhận danh sách từ server
def receive_file_list(client_socket):
    # Nhận độ dài chuỗi 
    data_length = client_socket.recv(4)
    data_length = struct.unpack('!I', data_length)[0]
    # Nhận chuỗi 
    data = client_socket.recv(data_length).decode()
    # Chuyển chuỗi thành danh sách
    file_list = data.split(',') if data else []
    return file_list

# Hàm lấy danh sách file cần download từ input.txttxt
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

# Hàm lấy danh sách những file đã downloadoad
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

# Hàm download 1 phần của filefile
def receive_part(client_socket, filename, start_end, progress_bar, percentage_label):
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
    total_byte = end - start
    total_recv = 0
    if total_byte > 0:
        with open(filename, "r+b") as file_obj:
            file_obj.seek(start)
            while total_recv < total_byte:
                bytes_read = part_connect.recv(min(BUFFER_SIZE, total_byte - total_recv))
                if not bytes_read:
                    break
                file_obj.write(bytes_read)
                total_recv += len(bytes_read)
                # Cập nhật giao diện thanh tiến trình
                progress = int((total_recv / total_byte) * 100)
                progress_bar["value"] = progress
                percentage_label["text"] = f"{progress}%"
                root.update_idletasks()  # Cập nhật giao diện

    part_connect.close()

# Hàm download file
def receive_file(client_socket, filename, filesize):
    log_message(f"Receiving {filename}...")
    unit = int(filesize / 4)
    length_of_chunk = [(0, unit),(unit, 2 * unit),(2 * unit, 3 * unit),(3 * unit, filesize)]

    # Tạo cửa sổ hiển thị tiến trình
    progress_window = tk.Toplevel(root)
    progress_window.title(f"Tiến trình tải {filename}")

    # Danh sách thanh tiến trình và nhãn phần trăm cho mỗi chunk
    progress_bars = []
    percentage_labels = []

    for i in range(len(length_of_chunk)):
        frame = tk.Frame(progress_window)
        frame.pack(pady=5, padx=10, fill=tk.X)

        label = tk.Label(frame, text=f"Chunk {i + 1}:")
        label.pack(side=tk.LEFT, padx=5)

        progress_bar = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate")
        progress_bar.pack(side=tk.LEFT, padx=5)
        progress_bars.append(progress_bar)

        percentage_label = tk.Label(frame, text="0%")
        percentage_label.pack(side=tk.LEFT, padx=5)
        percentage_labels.append(percentage_label)

    threads = []
    with open(filename, "wb") as file_obj:
        file_obj.write(b'\x00' * filesize)

    with open(DOWNLOADED_FILE, 'a') as file_obj:
        file_obj.write(filename + "\n")
    
    for i in range(len(length_of_chunk)):
        thread = threading.Thread(
            target=receive_part,
            args=(client_socket, filename, length_of_chunk[i], progress_bars[i], percentage_labels[i])
        )
        threads.append(thread)
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()

    log_message(f"Đã tải xong file {filename}")
    time.sleep(2)
    progress_window.destroy()

# Hàm lấy tên file, kích thước từ chuỗi có dang "name - size bytesbytes"
def get_filename_filesize(file):
    filename, filesize = file.split('-')
    filename = filename[:-1]
    filesize = filesize[1:]
    size, byte = filesize.split(' ')
    return filename, int(size)

# Hàm kết nối tới Server
def connect_to_server():
    try: 
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        messagebox.showinfo("Thông báo", "Đã kết nối tới server!")
        client_socket.send("0".encode())
        # Nhận danh sách các file có thể download
        file_list = receive_file_list(client_socket)
        display_list = receive_file_list(client_socket)
        filename_list = []
        filesize_list = []
        log_message(f"Danh sách file có thể download từ Server: ")
        for file in display_list:
            log_message(file)
        for file in file_list:
            name, size = get_filename_filesize(file)
            filename_list.append(name)
            filesize_list.append(size)

        # Nhập danh sách các file muốn download
        log_message("Nhập danh sách file muốn download vào file input.txt")
        input_file = []
        # Nhận và tải các file
        checked_file = []
        downloaded_file = []
        while True:
            log_message("Đang quét file input")
            input_file = get_files_to_download()
            downloaded_file = get_downloaded_file()
            for file in input_file:
                if file not in checked_file:
                    if file in filename_list and file not in downloaded_file:
                        i = filename_list.index(file)
                        size = filesize_list[i]
                        receive_file(client_socket, file, size)
                    elif file not in filename_list:
                        log_message(f"[!] File {file} không tồn tại")
                    elif file in downloaded_file:
                        log_message(f"[!] File {file} đã được tải")
                    checked_file.append(file)
            time.sleep(5)
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể kết nối tới server: {e}") 

def handle_exit(signal_received, frame):
    """Hàm xử lý khi người dùng nhấn Ctrl + C."""
    log_message("\n[!] Ctrl + C được nhấn. Đang đóng kết nối...")
    client_socket.send("close".encode())
    if client_socket:
        try:
            client_socket.close()  # Đóng socket nếu đang kết nối
            log_message("[+] Kết nối đã được đóng.")
            time.sleep(3)
        except Exception as e:
            log_message(f"[!] Lỗi khi đóng socket: {e}")
    sys.exit(0)  # Thoát chương trình

# Hàm chạy chương trình trong luồng riêng
def start_program():
    start_button.config(state="disabled")
    threading.Thread(target=connect_to_server, daemon=True).start()


# Gắn xử lý tín hiệu Ctrl + C
signal.signal(signal.SIGINT, handle_exit)               

# Tạo cửa sổ chính
root = tk.Tk()
root.title("TCP Client")

# Tạo một khung có thanh cuộn
log_display = ScrolledText(root, width=60, height=20, wrap=tk.WORD)
log_display.pack(padx=10, pady=10)

# Tạo nút để bắt đầu chương trình
start_button = tk.Button(root, text="Chạy chương trình", command=start_program)
start_button.pack(pady=10)

# Bắt đầu vòng lặp giao diện
root.mainloop()