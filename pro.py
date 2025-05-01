import socket
from _thread import start_new_thread
from urllib.parse import urlparse
import random
import time
import select

buffer_size = 8192

def proxy(ip, port):
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind((ip, port))
    proxy_socket.listen(10)
    print(f"Прокси запущен {ip}:{port}")
    while True:
        try:
            client_socket, addr = proxy_socket.accept()
            start_new_thread(client, (client_socket,))
        except Exception as e:
            print({e})


def client(client_socket):
    server_socket = None
    try:
        request = client_socket.recv(buffer_size)
        if not request:
            return
        if request.startswith(b'CONNECT'):
            https(client_socket, request)
            return
        try: #парсинг
            first_line = request.split(b'\r\n')[0].decode('ascii', errors='ignore')
            method, full_url, http_version = first_line.split()
            full_url = full_url.encode('ascii') if isinstance(full_url, str) else full_url
        except:
            return
        try:
            parsed_url = urlparse(
                full_url.decode('ascii', errors='ignore') if isinstance(full_url, bytes) else full_url)
            host = parsed_url.netloc
            if not host:
                for line in request.split(b'\r\n'):
                    if line.startswith(b'Host:'):
                        host = line.split(b':')[1].strip().decode('ascii', errors='ignore')
                        break
            if not host:
                return

            port = parsed_url.port if parsed_url.port else 80
            path = parsed_url.path if parsed_url.path else '/'
            query = f"?{parsed_url.query}" if parsed_url.query else ''
            display_url = f"http://{host}{path}" if not full_url.startswith(b'http') else full_url.decode('ascii',
                                                                                                          errors='ignore')
            unique_param = f"_={int(time.time())}{random.randint(0, 1000)}"
            new_query = f"{query}&{unique_param}" if query else f"?{unique_param}"
            new_path = f"{path}{new_query}"

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((host.split(':')[0], port))

            headers = {
                'Host': host,
                'Connection': 'close',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }

            request_line = f"{method} {new_path} {http_version}"
            headers_str = '\r\n'.join(f"{k}: {v}" for k, v in headers.items())
            new_request = f"{request_line}\r\n{headers_str}\r\n\r\n".encode()

            server_socket.sendall(new_request)

            response = server_socket.recv(buffer_size)
            if response:
                status_line = response.split(b'\r\n')[0].decode('ascii', errors='ignore')
                status_parts = status_line.split(' ')
                status_code = status_parts[1] if len(status_parts) > 1 else "000"
                status_text = ' '.join(status_parts[2:]) if len(status_parts) > 2 else "Unknown"
                print(f"{display_url} - {status_code} {status_text}")

                client_socket.sendall(response)
                while True:
                    try:
                        data = server_socket.recv(buffer_size)
                        if not data:
                            break
                        client_socket.sendall(data)
                    except:
                        break

        except Exception as e:
            print({e})
    except Exception as e:
        print({str(e)})
    finally:
        try:
            client_socket.close()
        except:
            pass
        try:
            if server_socket:
                server_socket.close()
        except:
            pass

def https(client_socket, request):
    try:
        host_port = request.split(b' ')[1].decode('ascii', errors='ignore')
        host, port = host_port.split(':') if ':' in host_port else (host_port, 443)
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(30)
        server_socket.connect((host, int(port)))

        sockets = [client_socket, server_socket]  #проксирование
        while True:
            readable, _, _ = select.select(sockets, [], [])
            for sock in readable:
                data = sock.recv(buffer_size)
                if not data:
                    return
                if sock is client_socket:
                    server_socket.sendall(data)
                else:
                    client_socket.sendall(data)
    except Exception as e:
        print({str(e)})
    finally:
        try:
            client_socket.close()
        except:
            pass
        try:
            server_socket.close()
        except:
            pass

if __name__ == "__main__":
    proxy("127.0.0.1", 8080)