import socket
import time
import tqdm
import sys
import signal
import struct

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
BUFFER_SIZE = 1024  # 1KB
INPUT_FILE = "input.txt"
DOWNLOADED_FILE = "downloaded_files.txt"

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = (SERVER_HOST, SERVER_PORT)

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
    print(f"Download file {filename}")
    with open(filename, "wb") as file_obj:
        file_obj.write(b'\x00' * size)
        progress = tqdm.tqdm(range(size), f"Tiến trình download: ", unit="B", unit_scale=True, unit_divisor=1024)
        while total_received < size:
            part, server = client_socket.recvfrom(BUFFER_SIZE + 8)
            seq_num = part[0:4]
            sum = part[4:8]
            seq_num = struct.unpack('!I', seq_num)[0]
            sum = struct.unpack('!I', sum)[0]
            content = part[8:BUFFER_SIZE + 8]
            cnt_sum = count_sum(content)
            if sum == cnt_sum:
                file_obj.seek(seq_num*BUFFER_SIZE)
                file_obj.write(content)
                total_received += len(content)
                progress.update(len(content))
                client_socket.sendto("1".encode(), server_address)
            else:
                client_socket.sendto("0".encode(), server_address)
        progress.close()
    if total_received == size:
        print(f"Đã tải thành công file {filename}")
        with open(DOWNLOADED_FILE, "a") as file_obj:
            file_obj.write(filename + '\n')
    else:
        print(f"Nhận được {total_received} so với {size} Bytes")

def handle():
    client_socket.sendto(b"0", server_address)
    file_list = receive_file_list(client_socket)
    display = receive_file_list(client_socket)
    list_namefile = []
    list_sizefile = []
    print("Danh sách các file có thể download từ server:")
    for file in display:
        print(file)
        
    for file in file_list:
        name, size = get_filename_filesize(file)
        list_namefile.append(name)
        list_sizefile.append(size)

    downloaded_file =[]
    checked_file = []
    print("Nhập vào file Input")
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
                        print(f"[!] File {file} không tồn tại")
                    elif file in downloaded_file:
                        print(f"[!] File {file} đã tải xuống")
                    checked_file.append(file)
        time.sleep(5)
        print("Dang quet file input")

def handle_exit(signal_received, frame):
    print("\n[!] Ctrl + C được nhấn. Đang đóng kết nối...")
    if client_socket:
        try:
            client_socket.close()  # Đóng socket nếu đang kết nối
            print("[+] Kết nối đã được đóng.")
        except Exception as e:
            print(f"[!] Lỗi khi đóng socket: {e}")
    sys.exit(0)  # Thoát chương trình


# Gắn xử lý tín hiệu Ctrl + C
signal.signal(signal.SIGINT, handle_exit) 

if __name__ == "__main__":
    handle()

