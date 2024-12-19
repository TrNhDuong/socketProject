import socket
import os
import threading
import struct

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
BUFFER_SIZE = 1024  # 1KB
FILE_DIRECTORY = "fordown\\"  # Thư mục chứa các file

display = []
file_list = []

# Tạo socket Server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((SERVER_HOST, SERVER_PORT))

# Hàm lấy file trong fordown
def get_file_list():
    file_list = []
    if os.path.exists(FILE_DIRECTORY):
        for filename in os.listdir(FILE_DIRECTORY):
            file_path = os.path.join(FILE_DIRECTORY, filename)
            if os.path.isfile(file_path):
                filesize = os.path.getsize(file_path)
                file_list.append(f"{filename} - {filesize} Bytes")
    return file_list

# Hàm đọc file chứa tên và dung lượnglượng
def read_contain_file():
    with open("listfile.txt", "r") as file_obj:
        lines = []
        for line in file_obj.readlines():
            if line.strip():
                lines.append(line.strip())
    return lines

# Hàm gửi danh sách file cho clientclient
def send_file_list(server_socket, address, file_list):
    # Chuyển mảng thành chuỗi, các file cách nhau bởi dấu ','
    file_list_data = ','.join(file_list)
    data_length = len(file_list_data)
    parts = [file_list_data[i:i+BUFFER_SIZE] for i in range(0, data_length, BUFFER_SIZE)]
    total_parts = len(parts)
    numPacket = struct.pack('!I', total_parts)
    server_socket.sendto(numPacket, address)
    for i, part in enumerate(parts):
        seq_num = struct.pack('!I', i)
        server_socket.sendto(seq_num + part.encode(), address)

# Hàm nhận 
def receive_namefile():
    lenName, addr = server_socket.recvfrom(4)
    lenName = struct.unpack('!I', lenName)[0]
    filename, saddr = server_socket.recvfrom(lenName)
    filename = filename.decode()
    return filename

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

def send_chunk_udp(add, parts, start, end):
    i = start
    while i < end:
        seq = struct.pack('!I', i)
        check_sum = count_sum(parts[i])
        check_sum = struct.pack('!I', check_sum)
        server_socket.sendto(seq + check_sum + parts[i], add)
        server_socket.settimeout(5)
        try:
            ACK, client = server_socket.recvfrom(1)
            if ACK.decode() == "1":
                i += 1
        except (server_socket.timeout, TimeoutError):
            continue


def send_file_udp(filename, address): 
    try:
        with open(FILE_DIRECTORY + filename, "rb") as file:
            file_data = file.read()
        
        # Chia dữ liệu thành các phần nhỏ
        total_size = len(file_data)
        parts = []
        for i in range(0, total_size, BUFFER_SIZE):
            parts.append(file_data[i:i+BUFFER_SIZE])
        total_parts = len(parts)
        
        unit = int(total_parts/4)
        length_of_chunk = [(0,unit), (unit, 2*unit), (2*unit, 3*unit), (3*unit, total_parts)]

        threads = []
        for i in range(4):
            idx, add = server_socket.recvfrom(1)
            idx = int(idx)
            start, end = length_of_chunk[idx]
            thread = threading.Thread(target=send_chunk_udp, args=(add, parts, start, end))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
        print(f"Đã gửi file {filename}")
    except FileNotFoundError:
        print(f"File not found: {filename}")


def handle_client(addr):
    send_file_list(server_socket, addr, file_list)
    send_file_list(server_socket, addr, display)
    while True:
        server_socket.settimeout(5)
        try:
            filename = receive_namefile()
            send_file_udp(filename, addr)
        except TimeoutError:
            continue


if __name__ == "__main__":
    display = read_contain_file()
    file_list = get_file_list()
    print("Các file có thể download trên Server: " )
    for file in display:
        print(file)
    data, addr = server_socket.recvfrom(1)
    if data.decode() == "0":
        print(f"[+] Message form {addr}")
        handle_client(addr)

server_socket.close()





