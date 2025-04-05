import docker
import time
import threading
from config import PORT_IN_CONTAINER, PORT_RANGE
from database import execute_query, remove_container_from_db

client = docker.from_env()
used_ports = set()

# Проверка, свободен ли порт
def is_port_free(port):
    for container in client.containers.list():
        container_ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        for port_binding in container_ports.get(f"{PORT_IN_CONTAINER}/tcp", []):
            if port_binding['HostPort'] == str(port):
                return False
    return True

# Получение свободного порта
def get_free_port():
    available_ports = list(set(PORT_RANGE) - used_ports)
    for port in available_ports:
        if is_port_free(port):
            used_ports.add(port)
            return port
    return None

# Удаление контейнера
def remove_container(container_id, port):
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
        print(f"[SUCCESS] Container {container_id} removed.")
    except docker.errors.NotFound:
        print(f"[WARNING] Container {container_id} not found in Docker, but still in database.")

    used_ports.discard(port)

    execute_query("DELETE FROM containers WHERE id = ?", (container_id,))
    print(f"[SUCCESS] Container {container_id} removed from database.")

# Автоматическое удаление контейнера после истечения времени жизни
def auto_remove_containers():
    try:
        while True:
            containers = execute_query("SELECT id, expiration_time, port FROM containers")
            if not containers:
                time.sleep(30)
                continue

            current_time = int(time.time())
            for container in containers:
                container_id, expiration_time, port = container
                expiration_time = int(expiration_time)

                time_to_wait = expiration_time - current_time

                if time_to_wait <= 0:
                    remove_container(container_id, port)

            time.sleep(30)

    except Exception as e:
        print(f"[FATAL] Unexpected error: {e}")
