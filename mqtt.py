import time
import paho.mqtt.client as mqtt
import sys
import threading
import csv
import pandas as pd
from tabulate import tabulate

# Konfigurasi MQTT
BROKER = "test.mosquitto.org"  # Ganti jika pakai broker lain
PORT = 1883
TOPIC = "dinusrobotic/bbm"

# Variabel penyimpanan
data_list = []  # Simpan 10 data per batch
average_list = []  # Simpan 10 hasil rata-rata
trial_counter = 1  # Menandai percobaan keberapa
MAX_TRIALS = 10  # Batas percobaan maksimal

# Variabel monitoring
last_time = time.time()

def calculate_average():
    """Menghitung rata-rata dari 10 data terakhir"""
    global trial_counter
    if len(data_list) == 10:
        avg_latency = sum(d[2] for d in data_list) / 10
        avg_bandwidth = sum(d[3] for d in data_list) / 10
        average_list.append([trial_counter, avg_latency, avg_bandwidth])
        save_to_csv()  # Simpan data setiap batch selesai
        
        if trial_counter >= MAX_TRIALS:
            print("\n🎉 Percobaan selesai! Program akan berhenti...\n")
            save_to_csv()  # Simpan terakhir kali sebelum keluar
            sys.exit(0)  # Hentikan program
        
        trial_counter += 1  # Naikkan nomor percobaan
        return True
    return False

def reset_data():
    """Reset semua data"""
    global data_list, average_list, trial_counter
    data_list.clear()
    average_list.clear()
    trial_counter = 1
    print("\n⚠️ Semua data telah direset dari CMD! ⚠️\n")

def save_to_csv():
    """Simpan data ke  Excel"""
    # Simpan Data Masuk (Append Mode)
    with open("data_masuk.xlsx", mode="a", newline="") as file:
        writer = csv.writer(file)
        if file.tell() == 0:  # Jika file kosong, tulis header dulu
            writer.writerow(["Percobaan Ke", "No", "Latency (s)", "Bandwidth (kbps)"])
        writer.writerows(data_list)

    # Simpan Data Rata-rata (Append Mode)
    df = pd.DataFrame(average_list, columns=["Percobaan Ke", "Rata-rata Latency (s)", "Rata-rata Bandwidth (kbps)"])
    df.to_csv("data_rata_rata.xlsx", mode="a", header=not pd.io.common.file_exists("data_rata_rata.xlsx"), index=False)
    
    # Simpan ke Excel (overwrite tetap perlu karena Excel tidak bisa append langsung)
    df.to_excel("data_rata_rata.xlsx", index=False)
    
    print("\n✅ Data telah disimpan ke CSV & Excel!\n")

def print_tables():
    """Menampilkan tabel data & rata-rata"""
    print("\n📊 Data Masuk (10 Terakhir):")
    headers = ["Percobaan Ke", "No", "Latency (s)", "Bandwidth (kbps)"]
    print(tabulate(data_list, headers, tablefmt="grid"))

    print("\n📈 Tabel Rata-rata:")
    avg_headers = ["Percobaan Ke", "Rata-rata Latency (s)", "Rata-rata Bandwidth (kbps)"]
    print(tabulate(average_list, avg_headers, tablefmt="grid"))

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker!")

def on_message(client, userdata, msg):
    global last_time

    if trial_counter > MAX_TRIALS:
        print("\n⛔ Maksimal percobaan telah tercapai! Program berhenti.\n")
        client.disconnect()
        sys.exit(0)

    message_size_bytes = sys.getsizeof(msg.payload)
    message_size_bits = message_size_bytes * 8  

    current_time = time.time()
    elapsed_time = current_time - last_time if last_time else 0
    last_time = current_time

    bandwidth_kbps = (message_size_bits / 1000) / elapsed_time if elapsed_time > 0 else 0

    data_list.append([trial_counter, len(data_list) + 1, elapsed_time, bandwidth_kbps])

    if calculate_average():
        data_list.clear()

    print_tables()

def listen_for_reset():
    """Mendengarkan input CMD untuk reset"""
    while True:
        command = input()
        if command.strip().lower() == "reset":
            reset_data()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.subscribe(TOPIC)

# Jalankan thread untuk reset dari CMD
threading.Thread(target=listen_for_reset, daemon=True).start()

# Jalankan MQTT client
client.loop_forever()
