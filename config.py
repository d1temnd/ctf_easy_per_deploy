import os


db_path = './containers.db'
leave_time = os.getenv('LEAVE_TIME')
add_time = os.getenv('ADD_TIME')
images_name = os.getenv('IMAGES_NAME')
port_in_container = os.getenv('PORT_IN_CONTAINER')
PORT_RANGE = range(os.getenv('START_RANGE'), os.getenv('STOP_RANGE'))


# leave_time = 240  # Время жизни контейнера (сек)
# add_time = 120  # Время продления контейнера (сек)
# images_name = "d1temnd/task_images_ozo:1.0.1"
# port_in_container = "80"
# PORT_RANGE = range(9000, 10001)
