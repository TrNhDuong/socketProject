import socket
import os
import threading
import struct

# Server configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5001
BUFFER_SIZE = 1024  # 1KB
FILE_DIRECTORY = "fordown"  # Thư mục chứa các file

# Mảng chứa các địa chỉ đã kết nối
connected_addr = []
file_list = []

# Tạo socket server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(5)
print(f"[*] Đang lắng nghe tại {SERVER_HOST}:{SERVER_PORT}")

# Hàm đọc file chứa tên và dung lượnglượng
def read_contain_file():
    with open("listfile.txt", "r") as file_obj:
        lines = []
        for line in file_obj.readlines():
            if line.strip():
                lines.append(line.strip())
    return lines

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

# Hàm gửi danh sách file
def send_file_list(client_socket, file_list):
    # Chuyển mảng thành chuỗi ngăn cách bởi dấu ',' giữa các filefile
    data = ','.join(file_list)
    data_length = len(data)
    packed_length = struct.pack('!I', data_length)  # '!I': big-endian, unsigned int (4 byte)
    # Gửi độ dài trước
    client_socket.send(packed_length)
    # Gửi toàn bộ chuỗi
    client_socket.sendall(data.encode())

# Hàm gửi chunk tới Client
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
    print(f"Nhận được kết nối từ {address}")
    print(f"Đã gửi danh sách cho {address}")
    # Gửi danh sách file cho clien
    display = read_contain_file()
    send_file_list(client_socket, file_list)
    send_file_list(client_socket, display)
    message = client_socket.recv(5).decode()
    if message == "close":
        print("[+] Client address ", address ," closed")


def connect_from_client(client_socket, address):
    signal = client_socket.recv(1).decode('utf-8')  # Chỉ nhận 1 byte
    # Xử lí kết nối
    if signal == "0":
        handle_client(client_socket, address)
    else:
        # Nhận xâu chứa tên file muốn tải, byte bắt đầu và kết thúc từ client
        lenStr = client_socket.recv(4)
        lenStr = struct.unpack('!I', lenStr)[0]
        mess = client_socket.recv(lenStr).decode()
        filename, start, end = mess.split(',')
        start, end = int(start), int(end)
        send_chunk(client_socket, filename, start, end)
    client_socket.close()


# Vòng lặp chính của server
if __name__ == "__main__":
    file_list = get_file_list()
    dis = read_contain_file()
    print("Các file có thể download từ Server:")
    for file in dis:
        print(file)
    while True:
        client_socket, address = server_socket.accept()
        client = threading.Thread(target=connect_from_client, args=(client_socket, address))
        client.start()

# Đóng server socket (khi thoát)
server_socket.close()