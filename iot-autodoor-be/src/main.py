from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from websockets import client
from PIL import Image
from io import BytesIO
import os
import json

app = FastAPI()

origins = [
  "http://localhost",  
  "http://localhost:3000", 
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/")
def read_root():
  return {"message": "Hello, World!"}


@app.websocket("/recognize")
async def warning_enpoint(server: WebSocket):
  try:
    await server.accept()
    print("Start '/recognize'")

    # Xử lý lấy tên người được cấp quyền mở cửa
    text_file_path = "D:/Workspace/Python/iot-autodoor-be/user_open_door.txt"
    names = []
    with open(text_file_path, 'r') as file:
      content = file.read()
      if not content.strip() == "":
        names = content.split(",")

    # Gửi danh sách tên đã được cấp quyền mở cửa
    await server.send_json(json.dumps({
      "users": names
    }))

    print("'/recognize' is connecting to ESCP32-CAM...")

    async with client.connect("ws://192.168.207.38:60/") as socket:
      print("'/recognize' connected to ESCP32-CAM") 
      while True:
        blob = await socket.recv() # Receive data

        # Handle recognize face here

        await server.send_bytes(BytesIO(blob).read()) # Send data after recognize
  except Exception as err:
    print(f"Error in /recognize: {err}")

@app.websocket("/train")
async def warning_enpoint(server: WebSocket):
  try:
    await server.accept()
    print("Start '/train'")
    text_file_path = "D:/Workspace/Python/iot-autodoor-be/user_open_door.txt"
    images_folder_path = "D:/Workspace/Python/iot-autodoor-be/images/"
    while True:
      message = await server.receive_json()
      names = []
      print(message)
      if message["action"] == "add":

        # Xử lý lấy tên người được cấp quyền mở cửa
        with open(text_file_path, 'r') as file:
          content = file.read()
          if not content.strip() == "":
            names = content.split(",")
        
        # Kiểm tra trùng tên
        if message["user"] not in names:
          print("'/train' is connecting to ESCP32-CAM...")
          async with client.connect("ws://192.168.207.38:60/") as socket:
            print("'/train' connected to ESCP32-CAM") 
            for num in range(1, 51):
              print(f"Received data ({num})")
              blob = await socket.recv()
              image = Image.open(BytesIO(blob))
              image.save(f'{images_folder_path}{message["user"]}-{num}.jpg')
          
          # Train new model here
          #...

          # Xử lý ghi lại file text
          names.append(message["user"])
          with open(text_file_path, 'w') as file:
            file.write(','.join(names))
          
          # Gửi thông báo train thành công
          await server.send_json(json.dumps({
            "users": names,
            "status": "train success"
          }))
        else:
          # Gửi thông báo tên đã được sử dụng
          await server.send_json(json.dumps({
            "users": names,
            "status": "namesake"
          }))
      else: 
        if message["action"] == "delete":
          # Xử lý lấy tên và xóa tên khỏi file lưu trữ tên người được cấp quyền mở cửa
          with open(text_file_path, 'r') as file:
            content = file.read()
            names = content.split(",")
          names.remove(message["user"])
          
          # Xóa ảnh
          for filename in os.listdir(images_folder_path):
            if filename.startswith(f'{message["user"]}-') and filename.endswith('.jpg'):
              image_path = os.path.join(images_folder_path, filename)
              os.remove(image_path)
              print(f"Đã xóa: {filename}")

          # Retrain model here
          #...

          # Xử lý ghi lại file text
          with open(text_file_path, 'w') as file:
            file.write(','.join(names))
          
          # Gửi thông báo xóa tên thành công
          await server.send_json(json.dumps({
            "users": names,
            "status": "delete success"
          }))
        else:
          # Xử lý xóa toàn bộ tên người dùng
          with open(text_file_path, 'w') as file:
            file.write("")
          
          # Gửi thông báo xóa tên thành công
          await server.send_json(json.dumps({
            "users": [],
            "status": "delete all success"
          }))
  except Exception as err:
    await server.send_json(json.dumps({
      "status": "error"
    }))


if __name__ == "__main__":
  uvicorn.run("main:app", port=8000, log_level="info")