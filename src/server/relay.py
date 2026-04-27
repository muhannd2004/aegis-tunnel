import asyncio
import random

from src.shared.protocol import pack_message, read_message

PUBLIC_PORT = 8080
TUNNEL_PORT = 7000

active_tunnel_reader = None
active_tunnel_writer = None

active_users = {}

async def handle_tunnel_connection(reader, writer):
    global active_tunnel_reader, active_tunnel_writer

    active_tunnel_reader = reader
    active_tunnel_writer = writer

    addr = writer.get_extra_info('peername')

    print(f"[*] TUNNEL ESTABLISHED: connected from {addr}")

    try:
        while True:
            connection_id, payload = await read_message(reader)

            if payload is None:
                break

            if connection_id in active_users:
                user_writer = active_users[connection_id]
                user_writer.write(payload)
                await user_writer.drain()
            else:
                print(f"[-] Dropping packet: User {connection_id} already disconnected.")

        await writer.wait_closed()
    except Exception as e:
        pass
    finally:
        print("[-] TUNNEL BROKEN: disconnected.")
        active_tunnel_reader = None
        active_tunnel_writer = None
        writer.close()


async def handle_public_traffic(reader, writer):
    global active_tunnel_writer

    addr = writer.get_extra_info('peername')
    if active_tunnel_writer is None:
        print(f"[-] Dropping public request from {addr}: No tunnel active.")
        writer.close()
        return


    cur_connection_id = random.randint(1, 4000000000)
    while cur_connection_id in active_users:
        cur_connection_id = random.randint(1, 4000000000)

    active_users[cur_connection_id] = writer

    print(f"[+] Public request from {addr}")

    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break

            packed_chunk = pack_message(cur_connection_id, chunk)
            active_tunnel_writer.write(packed_chunk)
            await active_tunnel_writer.drain()

    except Exception as e:
        pass
    # because of stay-alive this won't get executed unless after the user disconnect or erroe
    finally:
        active_users.pop(cur_connection_id, None)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        print(f"[-] Public connection {cur_connection_id} closed.")

async def main():
    public_server = await asyncio.start_server(
        handle_public_traffic, '0.0.0.0', PUBLIC_PORT
    )

    tunnel_server = await asyncio.start_server(
        handle_tunnel_connection, '0.0.0.0', TUNNEL_PORT
    )


    async with public_server, tunnel_server:
        await asyncio.gather(
            public_server.serve_forever(),
            tunnel_server.serve_forever()
        )

if __name__ == "__main__":
    asyncio.run(main())
