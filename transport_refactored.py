from dataclasses import dataclass
from datetime import datetime

DATE_FORMAT = "%Y-%m-%d %H:%M"

ROLE_EMPLOYEE = "employee"
ROLE_DISPATCHER = "dispatcher"

REQUEST_NEW = "NEW"
REQUEST_ASSIGNED = "ASSIGNED"
REQUEST_COMPLETED = "COMPLETED"

ASSIGNMENT_ASSIGNED = "ASSIGNED"
ASSIGNMENT_COMPLETED = "COMPLETED"


class TransportError(Exception):
    pass


@dataclass
class User:
    id: int
    full_name: str
    role: str


@dataclass
class Vehicle:
    id: int
    plate_number: str
    model: str
    capacity: int
    is_active: bool = True


@dataclass
class Driver:
    id: int
    full_name: str
    phone: str
    is_active: bool = True


@dataclass
class Request:
    id: int
    author_id: int
    purpose: str
    route: str
    departure_time: datetime
    return_time: datetime
    passengers_count: int
    status: str = REQUEST_NEW


@dataclass
class Assignment:
    id: int
    request_id: int
    vehicle_id: int
    driver_id: int
    dispatcher_id: int
    status: str = ASSIGNMENT_ASSIGNED


@dataclass
class Trip:
    id: int
    assignment_id: int
    fact_departure_time: datetime
    fact_return_time: datetime
    odometer_start: int
    odometer_end: int
    result: str


class TransportSystem:
    def __init__(self):
        self.users = {}
        self.vehicles = {}
        self.drivers = {}
        self.requests = {}
        self.assignments = {}
        self.trips = {}

        self.next_request_id = 1
        self.next_assignment_id = 1
        self.next_trip_id = 1

    def add_user(self, full_name, role):
        user_id = len(self.users) + 1
        user = User(user_id, full_name, role)
        self.users[user_id] = user
        return user

    def add_vehicle(self, plate_number, model, capacity):
        vehicle_id = len(self.vehicles) + 1
        vehicle = Vehicle(vehicle_id, plate_number, model, capacity)
        self.vehicles[vehicle_id] = vehicle
        return vehicle

    def add_driver(self, full_name, phone):
        driver_id = len(self.drivers) + 1
        driver = Driver(driver_id, full_name, phone)
        self.drivers[driver_id] = driver
        return driver

    def create_request(self, author_id, purpose, route, departure_time, return_time, passengers_count):
        author = self.get_user(author_id)
        departure_date = self.parse_date(departure_time)
        return_date = self.parse_date(return_time)

        self.validate_request_data(purpose, route, departure_date, return_date, passengers_count)

        request = Request(
            id=self.next_request_id,
            author_id=author.id,
            purpose=purpose.strip(),
            route=route.strip(),
            departure_time=departure_date,
            return_time=return_date,
            passengers_count=passengers_count,
        )
        self.requests[request.id] = request
        self.next_request_id += 1
        return request

    def assign_transport(self, request_id, vehicle_id, driver_id, dispatcher_id):
        request = self.get_request(request_id)
        vehicle = self.get_vehicle(vehicle_id)
        driver = self.get_driver(driver_id)
        dispatcher = self.get_user(dispatcher_id)

        self.check_dispatcher(dispatcher)
        self.check_request_before_assignment(request)
        self.check_vehicle_and_driver(vehicle, driver)
        self.check_vehicle_capacity(vehicle, request.passengers_count)
        self.check_vehicle_availability(vehicle.id, request.departure_time, request.return_time)

        assignment = Assignment(
            id=self.next_assignment_id,
            request_id=request.id,
            vehicle_id=vehicle.id,
            driver_id=driver.id,
            dispatcher_id=dispatcher.id,
        )
        self.assignments[assignment.id] = assignment
        self.next_assignment_id += 1

        request.status = REQUEST_ASSIGNED
        return assignment

    def close_trip(self, assignment_id, fact_departure_time, fact_return_time, odometer_start, odometer_end, result):
        assignment = self.get_assignment(assignment_id)
        request = self.get_request(assignment.request_id)
        fact_departure = self.parse_date(fact_departure_time)
        fact_return = self.parse_date(fact_return_time)

        self.validate_trip_data(assignment, fact_departure, fact_return, odometer_start, odometer_end, result)

        trip = Trip(
            id=self.next_trip_id,
            assignment_id=assignment.id,
            fact_departure_time=fact_departure,
            fact_return_time=fact_return,
            odometer_start=odometer_start,
            odometer_end=odometer_end,
            result=result.strip(),
        )
        self.trips[trip.id] = trip
        self.next_trip_id += 1

        assignment.status = ASSIGNMENT_COMPLETED
        request.status = REQUEST_COMPLETED
        return trip

    def get_user(self, user_id):
        user = self.users.get(user_id)
        if user is None:
            raise TransportError("Пользователь не найден")
        return user

    def get_vehicle(self, vehicle_id):
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is None:
            raise TransportError("Транспорт не найден")
        return vehicle

    def get_driver(self, driver_id):
        driver = self.drivers.get(driver_id)
        if driver is None:
            raise TransportError("Водитель не найден")
        return driver

    def get_request(self, request_id):
        request = self.requests.get(request_id)
        if request is None:
            raise TransportError("Заявка не найдена")
        return request

    def get_assignment(self, assignment_id):
        assignment = self.assignments.get(assignment_id)
        if assignment is None:
            raise TransportError("Назначение не найдено")
        return assignment

    def validate_request_data(self, purpose, route, departure_date, return_date, passengers_count):
        if not purpose.strip() or not route.strip():
            raise TransportError("Цель поездки и маршрут должны быть заполнены")
        if passengers_count <= 0:
            raise TransportError("Количество пассажиров должно быть больше нуля")
        if departure_date >= return_date:
            raise TransportError("Дата возвращения должна быть позже даты выезда")

    def check_dispatcher(self, dispatcher):
        if dispatcher.role != ROLE_DISPATCHER:
            raise TransportError("Назначать транспорт может только ответственный")

    def check_request_before_assignment(self, request):
        if request.status != REQUEST_NEW:
            raise TransportError("Назначить транспорт можно только для новой заявки")

    def check_vehicle_and_driver(self, vehicle, driver):
        if not vehicle.is_active:
            raise TransportError("Выбранный транспорт недоступен")
        if not driver.is_active:
            raise TransportError("Выбранный водитель недоступен")

    def check_vehicle_capacity(self, vehicle, passengers_count):
        if passengers_count > vehicle.capacity:
            raise TransportError("Вместимость транспорта меньше числа пассажиров")

    def check_vehicle_availability(self, vehicle_id, departure_date, return_date):
        if self.vehicle_is_busy(vehicle_id, departure_date, return_date):
            raise TransportError("На выбранный период транспорт уже занят")

    def validate_trip_data(self, assignment, fact_departure, fact_return, odometer_start, odometer_end, result):
        if assignment.status != ASSIGNMENT_ASSIGNED:
            raise TransportError("Поездка уже закрыта")
        if fact_departure >= fact_return:
            raise TransportError("Фактическое время возвращения должно быть позже выезда")
        if odometer_end < odometer_start:
            raise TransportError("Конечный пробег не может быть меньше начального")
        if not result.strip():
            raise TransportError("Нужно указать результат поездки")

    def vehicle_is_busy(self, vehicle_id, departure_date, return_date):
        for assignment in self.assignments.values():
            if assignment.vehicle_id != vehicle_id:
                continue

            request = self.requests[assignment.request_id]
            time_intersection = departure_date < request.return_time and return_date > request.departure_time

            if assignment.status in (ASSIGNMENT_ASSIGNED, ASSIGNMENT_COMPLETED) and time_intersection:
                return True

        return False

    def print_data(self):
        print("\nЗаявки:")
        for request in self.requests.values():
            print(request)

        print("\nНазначения:")
        for assignment in self.assignments.values():
            print(assignment)

        print("\nПоездки:")
        for trip in self.trips.values():
            print(trip)

    @staticmethod
    def parse_date(date_string):
        try:
            return datetime.strptime(date_string, DATE_FORMAT)
        except ValueError:
            raise TransportError(f"Неверный формат даты. Используйте {DATE_FORMAT}")


def main():
    system = TransportSystem()

    employee = system.add_user("Иванов Илья Петрович", ROLE_EMPLOYEE)
    dispatcher = system.add_user("Петрова Марина Сергеевна", ROLE_DISPATCHER)

    vehicle = system.add_vehicle("А123ВС54", "Lada Largus", 5)
    driver = system.add_driver("Сидоров Алексей Викторович", "+7-900-123-45-67")

    request = system.create_request(
        employee.id,
        "Поездка на склад за оборудованием",
        "Офис - склад №3 - офис",
        "2026-04-23 10:00",
        "2026-04-23 13:00",
        3,
    )

    assignment = system.assign_transport(request.id, vehicle.id, driver.id, dispatcher.id)

    system.close_trip(
        assignment.id,
        "2026-04-23 10:10",
        "2026-04-23 12:45",
        15200,
        15286,
        "Поездка выполнена успешно",
    )

    system.print_data()


if __name__ == "__main__":
    try:
        main()
    except TransportError as error:
        print("Ошибка:", error)
