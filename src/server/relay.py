import socket
import asyncio

active_tunnel_reader = None
active_tunnel_writer = None


async def handle_tunnel_connection(reader, writer):
    global active_tunnel_reader, active_tunnel_writer

    active_tunnel_reader = reader
    active_tunnel_writer = writer

    addr = writer.get_extra_info('peername')

    print(f"[*] TUNNEL ESTABLISHED: connected from {addr}")

    try:
        await writer.wait_closed()
    except Exception as e:
        pass
    finally:
        print("[-] TUNNEL BROKEN: disconnected.")
        active_tunnel_reader = None
        active_tunnel_writer = None
        writer.close()


async def handle_public_traffic(reader, writer):
    global active_tunnel_reader, active_tunnel_writer

    addr = writer.get_extra_info('peername')

    if active_tunnel_writer is None or active_tunnel_reader is None:
        print(f"[-] Dropping public request from {addr}: No tunnel active.")
        writer.close()
        return

    print(f"[+] Public request from {addr}")

    async def public_to_tunnel():
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            active_tunnel_writer.write(chunk)
            await active_tunnel_writer.drain()

    async def tunnel_to_public():
        while True:
            chunk = await active_tunnel_reader.read(4096)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()

    try:
        await asyncio.gather(
            public_to_tunnel(),
            tunnel_to_public()
        )
    except Exception as e:
        pass
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[-] Public connection closed for {addr}")

async def main():
    public_server = await asyncio.start_server(
        handle_public_traffic, '0.0.0.0', 8080
    )

    tunnel_server = await asyncio.start_server(
        handle_tunnel_connection, '0.0.0.0', 7000
    )


    async with public_server, tunnel_server:
        await asyncio.gather(
            public_server.serve_forever(),
            tunnel_server.serve_forever()
        )

if __name__ == "__main__":
    # This is how you kick off an asyncio program
    asyncio.run(main())
