import asyncio
from src.shared.protocol import pack_message, read_message
import argparse

TUNNEL_PORT = 7000
apps = None
ports = None
active_local_sockets = {}
AEGIS_SECRET = None
CLOUD_IP = '127.0.0.1'

async def pump_local_to_tunnel(connection_id, local_reader, tunnel_writer):

    try:
        while True:
            chunk = await local_reader.read(4096)

            if not chunk:
                break

            packed_chunk = pack_message(connection_id, chunk)

            tunnel_writer.write(packed_chunk)
            await  tunnel_writer.drain()

    except Exception as e:
        pass
    finally:
            if connection_id in active_local_sockets:
                writer = active_local_sockets.pop(connection_id)
                writer.close()

def get_target_port(raw_http_bytes):
    try:
        text = raw_http_bytes.decode('utf-8', errors='ignore')

        for line in text.split('\r\n'):
            if line.lower().startswith('host:'):
                domain = line.split(' ', 1)[1].split('.', 1)[0]

                if domain not in apps:
                    print("Error domain name does not exist just get 3000")
                    return 3000

                idx_port = apps.index(domain)
                return ports[idx_port]

    except Exception as e:
        pass

    return 3000

async def main():

    while True:
        try:
            tunnel_reader, tunnel_writer = await asyncio.open_connection(CLOUD_IP, TUNNEL_PORT)

            hand_shake = pack_message(0, AEGIS_SECRET.encode('utf-8', errors='ignore'))
            tunnel_writer.write(hand_shake)
            await tunnel_writer.drain()
            print("AUTHENTICATED! Tunnel established")

            while True:
                connection_id, payload = await read_message(tunnel_reader)

                if payload is None:
                    break

                try:
                    if connection_id not in active_local_sockets:
                        port = get_target_port(payload)
                        local_reader, local_writer = await asyncio.open_connection(CLOUD_IP, port)
                        active_local_sockets[connection_id] = local_writer
                        asyncio.create_task(pump_local_to_tunnel(connection_id, local_reader, tunnel_writer))

                    local_writer = active_local_sockets[connection_id]
                    local_writer.write(payload)
                    await local_writer.drain()
                except ConnectionRefusedError:
                    print(f"Nothing is running on Port !")
                    continue

        except Exception as e:
            print(f"[-] Network error: {e}")

        for writer in active_local_sockets.values():
            writer.close()
        active_local_sockets.clear()  # Empty the dictionary!

        print("[-] Retrying in 5 seconds...")
        await asyncio.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", nargs='+')
    parser.add_argument("--app", nargs='+')
    parser.add_argument('--auth', required=True, help="Secret key for the cloud tunnel")

    args = parser.parse_args()

    if len(args.app) != len(args.port):
        print("Invalid Input each port maps to app in order")

    apps = args.app
    ports = [int(x) for x in args.port]
    AEGIS_SECRET = args.auth

    asyncio.run(main())