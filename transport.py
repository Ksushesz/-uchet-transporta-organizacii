from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


DATETIME_FMT = "%Y-%m-%d %H:%M"


class TransportSystemError(Exception):
    """Base error for transport system demo."""


class ValidationError(TransportSystemError):
    pass


@dataclass
class User:
    user_id: int
    full_name: str
    role: str  # employee, dispatcher, admin


@dataclass
class Vehicle:
    vehicle_id: int
    plate_number: str
    model: str
    capacity: int
    is_active: bool = True


@dataclass
class Driver:
    driver_id: int
    full_name: str
    phone: str
    is_active: bool = True


@dataclass
class TransportRequest:
    request_id: int
    author_id: int
    goal: str
    route: str
    planned_departure: datetime
    planned_return: datetime
    passengers: int
    status: str = "NEW"  # NEW, ASSIGNED, COMPLETED, REJECTED


@dataclass
class Assignment:
    assignment_id: int
    request_id: int
    vehicle_id: int
    driver_id: int
    dispatcher_id: int
    status: str = "ASSIGNED"


@dataclass
class Trip:
    trip_id: int
    assignment_id: int
    actual_departure: datetime
    actual_return: datetime
    odometer_start: int
    odometer_end: int
    result: str


class TransportSystem:
    """Working demo of the key project scenario:
    create request -> assign transport -> close trip.
    """

    def __init__(self) -> None:
        self.users: Dict[int, User] = {}
        self.vehicles: Dict[int, Vehicle] = {}
        self.drivers: Dict[int, Driver] = {}
        self.requests: Dict[int, TransportRequest] = {}
        self.assignments: Dict[int, Assignment] = {}
        self.trips: Dict[int, Trip] = {}
        self._request_seq = 1
        self._assignment_seq = 1
        self._trip_seq = 1

    def add_user(self, full_name: str, role: str) -> User:
        user_id = len(self.users) + 1
        user = User(user_id, full_name, role)
        self.users[user_id] = user
        return user

    def add_vehicle(self, plate_number: str, model: str, capacity: int) -> Vehicle:
        vehicle_id = len(self.vehicles) + 1
        vehicle = Vehicle(vehicle_id, plate_number, model, capacity)
        self.vehicles[vehicle_id] = vehicle
        return vehicle

    def add_driver(self, full_name: str, phone: str) -> Driver:
        driver_id = len(self.drivers) + 1
        driver = Driver(driver_id, full_name, phone)
        self.drivers[driver_id] = driver
        return driver

    def create_request(
        self,
        author_id: int,
        goal: str,
        route: str,
        planned_departure: str,
        planned_return: str,
        passengers: int,
    ) -> TransportRequest:
        if author_id not in self.users:
            raise ValidationError("Пользователь не найден.")
        departure_dt = self._parse_dt(planned_departure)
        return_dt = self._parse_dt(planned_return)

        if departure_dt >= return_dt:
            raise ValidationError("Дата возврата должна быть позже даты выезда.")
        if passengers <= 0:
            raise ValidationError("Количество пассажиров должно быть больше нуля.")
        if not goal.strip() or not route.strip():
            raise ValidationError("Цель поездки и маршрут обязательны.")

        request_obj = TransportRequest(
            request_id=self._request_seq,
            author_id=author_id,
            goal=goal.strip(),
            route=route.strip(),
            planned_departure=departure_dt,
            planned_return=return_dt,
            passengers=passengers,
        )
        self.requests[self._request_seq] = request_obj
        self._request_seq += 1
        return request_obj

    def assign_transport(
        self,
        request_id: int,
        vehicle_id: int,
        driver_id: int,
        dispatcher_id: int,
    ) -> Assignment:
        if request_id not in self.requests:
            raise ValidationError("Заявка не найдена.")
        if vehicle_id not in self.vehicles:
            raise ValidationError("Транспорт не найден.")
        if driver_id not in self.drivers:
            raise ValidationError("Водитель не найден.")
        if dispatcher_id not in self.users:
            raise ValidationError("Ответственный пользователь не найден.")

        request_obj = self.requests[request_id]
        vehicle = self.vehicles[vehicle_id]
        driver = self.drivers[driver_id]
        dispatcher = self.users[dispatcher_id]

        if dispatcher.role != "dispatcher":
            raise ValidationError("Назначать транспорт может только ответственный.")
        if request_obj.status != "NEW":
            raise ValidationError("Назначить можно только новую заявку.")
        if not vehicle.is_active:
            raise ValidationError("Транспорт недоступен.")
        if not driver.is_active:
            raise ValidationError("Водитель недоступен.")
        if request_obj.passengers > vehicle.capacity:
            raise ValidationError("Вместимость транспорта меньше числа пассажиров.")
        if self._vehicle_is_busy(vehicle_id, request_obj.planned_departure, request_obj.planned_return):
            raise ValidationError("На выбранный период транспорт уже занят.")

        assignment = Assignment(
            assignment_id=self._assignment_seq,
            request_id=request_id,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            dispatcher_id=dispatcher_id,
        )
        self.assignments[self._assignment_seq] = assignment
        self._assignment_seq += 1
        request_obj.status = "ASSIGNED"
        return assignment

    def close_trip(
        self,
        assignment_id: int,
        actual_departure: str,
        actual_return: str,
        odometer_start: int,
        odometer_end: int,
        result: str,
    ) -> Trip:
        if assignment_id not in self.assignments:
            raise ValidationError("Назначение не найдено.")

        assignment = self.assignments[assignment_id]
        request_obj = self.requests[assignment.request_id]

        departure_dt = self._parse_dt(actual_departure)
        return_dt = self._parse_dt(actual_return)

        if departure_dt >= return_dt:
            raise ValidationError("Фактическое возвращение должно быть позже выезда.")
        if odometer_end < odometer_start:
            raise ValidationError("Конечный пробег не может быть меньше начального.")
        if assignment.status != "ASSIGNED":
            raise ValidationError("Поездка уже закрыта или недоступна для закрытия.")
        if not result.strip():
            raise ValidationError("Нужно указать результат поездки.")

        trip = Trip(
            trip_id=self._trip_seq,
            assignment_id=assignment_id,
            actual_departure=departure_dt,
            actual_return=return_dt,
            odometer_start=odometer_start,
            odometer_end=odometer_end,
            result=result.strip(),
        )
        self.trips[self._trip_seq] = trip
        self._trip_seq += 1

        assignment.status = "COMPLETED"
        request_obj.status = "COMPLETED"
        return trip

    def _vehicle_is_busy(self, vehicle_id: int, start_dt: datetime, end_dt: datetime) -> bool:
        for assignment in self.assignments.values():
            if assignment.vehicle_id != vehicle_id:
                continue
            req = self.requests[assignment.request_id]
            overlaps = start_dt < req.planned_return and end_dt > req.planned_departure
            if assignment.status in {"ASSIGNED", "COMPLETED"} and overlaps:
                return True
        return False

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        try:
            return datetime.strptime(value, DATETIME_FMT)
        except ValueError as exc:
            raise ValidationError(
                f"Неверный формат даты '{value}'. Используйте {DATETIME_FMT}."
            ) from exc

    def print_state(self) -> None:
        print("\n=== Заявки ===")
        for obj in self.requests.values():
            print(
                f"#{obj.request_id}: {obj.goal}, {obj.route}, "
                f"статус={obj.status}, пассажиров={obj.passengers}"
            )

        print("\n=== Назначения ===")
        for obj in self.assignments.values():
            print(
                f"#{obj.assignment_id}: заявка={obj.request_id}, "
                f"ТС={obj.vehicle_id}, водитель={obj.driver_id}, статус={obj.status}"
            )

        print("\n=== Поездки ===")
        for obj in self.trips.values():
            distance = obj.odometer_end - obj.odometer_start
            print(
                f"#{obj.trip_id}: назначение={obj.assignment_id}, "
                f"пробег={distance} км, результат={obj.result}"
            )


def demo() -> None:
    system = TransportSystem()

    employee = system.add_user("Иванов Илья Петрович", "employee")
    dispatcher = system.add_user("Петрова Марина Сергеевна", "dispatcher")
    system.add_vehicle("А123ВС54", "Lada Largus", capacity=5)
    system.add_driver("Сидоров Алексей Викторович", "+7-900-123-45-67")

    request_obj = system.create_request(
        author_id=employee.user_id,
        goal="Поездка на склад за оборудованием",
        route="Офис - склад №3 - офис",
        planned_departure="2026-04-23 10:00",
        planned_return="2026-04-23 13:00",
        passengers=3,
    )
    print(f"Создана заявка #{request_obj.request_id}")

    assignment = system.assign_transport(
        request_id=request_obj.request_id,
        vehicle_id=1,
        driver_id=1,
        dispatcher_id=dispatcher.user_id,
    )
    print(f"Создано назначение #{assignment.assignment_id}")

    trip = system.close_trip(
        assignment_id=assignment.assignment_id,
        actual_departure="2026-04-23 10:10",
        actual_return="2026-04-23 12:45",
        odometer_start=15200,
        odometer_end=15286,
        result="Поездка выполнена успешно",
    )
    print(f"Закрыта поездка #{trip.trip_id}")

    system.print_state()


if __name__ == "__main__":
    try:
        demo()
    except TransportSystemError as exc:
        print(f"Ошибка: {exc}")
