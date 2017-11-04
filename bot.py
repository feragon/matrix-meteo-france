from matrix_client.client import MatrixClient
import re
import pickle
from meteofranceapi import MeteoFranceAPI
import datetime
from threading import Timer
from credentials import MATRIX_PASSWORD, MATRIX_SERVER, MATRIX_USERNAME

client = MatrixClient(MATRIX_SERVER)
timers = {}
next_id = 0

try:
    storage = pickle.load(open("save.db", "rb"))
except FileNotFoundError:
    storage = {}


def show_help(room):
    room.send_text(
        "Commandes Météo France\n" +
        "!weather list: Donne toutes les villes enregistrées sur ce salon\n" +
        "!weather show [VILLE] [X]: Donne la météo actuelle pour la ville maintenant, ou pour les X prochains jours\n" +
        "!weather add [VILLE] [HEURE HH:MM] [X]: Donne la météo des X jours suivants tous les jours à l'heure donnée\n" +
        "!weather delete [ID]: Supprime une ville déjà enregistrée"
    )


def list_registered(room):
    if (room.room_id not in storage) or (len(storage[room.room_id]) == 0):
        room.send_text("Il n'y a pas d'enregistrements pour ce salon.")
    else:
        room.send_text(str(len(storage[room.room_id])) + " enregistrements.\n")
        i = 1
        for data in storage[room.room_id]:
            room.send_text(
                "ID: " + str(i) + " " + data['name'] + " " + str(data['nb_days']) + " jours à " +
                str(data['hour'])
            )
            i = i + 1


def add(room, command_part):
    if len(command_part) < 5:
        raise RuntimeError("Commande invalide")

    time_parts = command_part[3].split(":")
    if len(time_parts) != 2:
        raise RuntimeError("Heure invalide")

    try:
        t = datetime.time(hour=int(time_parts[0]), minute=int(time_parts[1]))
    except ValueError:
        raise RuntimeError("Heure invalide")

    try:
        nb_days = int(command_part[4])
    except ValueError:
        raise RuntimeError("Nombre de jours invalide")

    if nb_days < 1:
        raise RuntimeError("Nombre de jours invalide")

    city = add_city_record(room.room_id, command_part[2], t, nb_days)

    room.send_text(city.name + " ajouté")


def show(room, command_part):
    if len(command_part) == 3:
        nb_days = 1
    elif len(command_part) == 4:
        try:
            nb_days = int(command_part[3])
        except ValueError:
            raise RuntimeError("Nombre de jours invalide")
    else:
        raise RuntimeError("Commande invalide")

    city = MeteoFranceAPI.search(command_part[2])
    room.send_text("Météo pour les " + str(nb_days) + " prochains jours à " + city.name + "\n" +
                   show_forecast(city.id, nb_days))


def delete(room, command_part):
    if len(command_part) != 3:
        raise RuntimeError("Commande invalide")

    try:
        index = int(command_part[2])
    except ValueError:
        raise RuntimeError("Indice invalide")

    if index < 1 or index > len(storage[room.room_id]):
        raise RuntimeError("Indice invalide")

    room_storage = storage[room.room_id][index - 1]
    timers[room.room_id][room_storage['id']].cancel()
    del storage[room.room_id][index - 1]

    save_storage()

    room.send_text("Ville supprimée")


def on_invite(room_id, state):
    client.join_room(room_id)


def process_command(command, room):
    try:
        command_part = command.split(" ")
        if len(command_part) > 1:
            if command_part[1] == "list":
                list_registered(room)
            elif command_part[1] == "show":
                show(room, command_part)
            elif command_part[1] == "add":
                add(room, command_part)
            elif command_part[1] == "delete":
                delete(room, command_part)
            else:
                show_help(room)
        else:
            show_help(room)
    except RuntimeError as e:
        room.send_text(str(e))


def on_message(event):
    if event["content"]["msgtype"] != "m.text":
        return

    message = event['content']['body']
    if not re.match("^!weather", message):
        return

    room = client.get_rooms()[event["room_id"]]
    process_command(message, room)


def save_storage():
    pickle.dump(storage, open("save.db", "wb"))


def add_city_record(room_id, city, daily_hour, nb_days):
    global next_id

    storage_data = {
        'hour': daily_hour,
        'nb_days': nb_days,
        'id': next_id
    }

    next_id = next_id + 1

    city = MeteoFranceAPI.search(city)

    storage_data['city_id'] = city.id
    storage_data['name'] = city.name

    if room_id in storage:
        storage[room_id].append(storage_data)
    else:
        storage[room_id] = [storage_data]

    save_storage()
    schedule(room_id, storage_data)

    return city


def show_forecast(city_id, nb_days):
    forecasts = MeteoFranceAPI.get_forecast(city_id, nb_days).forecasts
    forecast_str = ""
    for forecast in forecasts:
        forecast_str = \
            forecast_str + "\n\n" + str(forecast.date) + " " + forecast.moment + ": " + str(forecast.description) + \
            "\nDétails:\n" + \
            "Vent: " + str(forecast.wind_speed) + "km/h (Rafales: " + str(forecast.gust_speed) + "km/h)\n" + \
            "Températures: minimum " + str(forecast.min_temperature) + "°C " + \
            "maximum: " + str(forecast.max_temperature) + "°C\n" + \
            "Indice UV: " + str(forecast.uv_index) + "\n" + \
            "Pluie: " + str(forecast.rain_probability) + "%" + \
            " Neige: " + str(forecast.snow_probability) + "%" +\
            " Gel:" + str(forecast.frost_probability) + "%"

    return forecast_str


def show_forecast_sched(room_id, storage_data):
    room = client.rooms[room_id]
    room.send_text("Météo de " + storage_data['name'] + ":\n" + show_forecast(storage_data['city_id'],
                                                                              storage_data['nb_days']))


def schedule(room_id, record):
    now = datetime.datetime.now()
    notification_time = datetime.datetime.combine(datetime.date.today(), record['hour'])

    if notification_time < now:
        notification_time = notification_time + datetime.timedelta(days=1)

    timer = Timer((notification_time - now).seconds, show_forecast_sched, (room_id, record))

    if room_id not in timers:
        timers[room_id] = {}

    timers[room_id][record['id']] = timer

    timer.start()


def main():
    global next_id
    client.login_with_password(MATRIX_USERNAME, MATRIX_PASSWORD)

    for room_id, records in storage.items():
        for record in records:
            if record['id'] > next_id:
                next_id = record['id'] + 1
            schedule(room_id, record)

    client.add_invite_listener(on_invite)
    client.add_listener(on_message, "m.room.message")
    client.start_listener_thread(3000)

    input()

    save_storage()
    client.logout()

    for room_timers in timers:
        for timer in room_timers:
            timer.cancel()


if __name__ == "__main__":
    main()
