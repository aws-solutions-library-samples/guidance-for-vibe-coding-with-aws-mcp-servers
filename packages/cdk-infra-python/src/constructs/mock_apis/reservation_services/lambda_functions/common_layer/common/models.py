from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Hotel:
    """
    Hotel model.
    """

    Id: int
    Code: str
    Name: str
    Address: str
    Phone: str
    Chain: dict[str, Any] = field(default_factory=dict)
    Brand: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Hotel":
        """Create a Hotel instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert Hotel instance to dictionary."""
        return {
            "Id": self.Id,
            "Code": self.Code,
            "Name": self.Name,
            "Address": self.Address,
            "Phone": self.Phone,
            "Chain": self.Chain,
            "Brand": self.Brand,
        }


@dataclass
class RoomType:
    """
    Room type model.
    """

    RoomCode: str
    RoomName: str
    BaseRate: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoomType":
        """Create a RoomType instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert RoomType instance to dictionary."""
        return {"RoomCode": self.RoomCode, "RoomName": self.RoomName, "BaseRate": self.BaseRate}


@dataclass
class Guest:
    """
    Guest model.
    """

    PersonName: dict[str, str]
    EmailAddress: list[dict[str, str]] = field(default_factory=list)
    ContactNumbers: list[dict[str, str]] = field(default_factory=list)
    DateOfBirth: str | None = None
    Gender: str | None = None
    Payments: list[dict[str, Any]] = field(default_factory=list)
    Comments: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Guest":
        """Create a Guest instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert Guest instance to dictionary."""
        result = {
            "PersonName": self.PersonName,
            "EmailAddress": self.EmailAddress,
            "ContactNumbers": self.ContactNumbers,
        }

        if self.DateOfBirth:
            result["DateOfBirth"] = self.DateOfBirth

        if self.Gender:
            result["Gender"] = self.Gender

        if self.Payments:
            result["Payments"] = self.Payments

        if self.Comments:
            result["Comments"] = self.Comments

        return result


@dataclass
class RoomStay:
    """
    RoomStay model.
    """

    CheckInDate: str
    CheckOutDate: str
    GuestCount: list[dict[str, int]]
    NumRooms: int
    Products: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoomStay":
        """Create a RoomStay instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert RoomStay instance to dictionary."""
        return {
            "CheckInDate": self.CheckInDate,
            "CheckOutDate": self.CheckOutDate,
            "GuestCount": self.GuestCount,
            "NumRooms": self.NumRooms,
            "Products": self.Products,
        }


@dataclass
class RoomPrices:
    """
    RoomPrices model.
    """

    TotalPrice: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoomPrices":
        """Create a RoomPrices instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert RoomPrices instance to dictionary."""
        return {"TotalPrice": self.TotalPrice}


@dataclass
class BookingInfo:
    """
    BookingInfo model.
    """

    BookedBy: str
    BookingDate: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BookingInfo":
        """Create a BookingInfo instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert BookingInfo instance to dictionary."""
        return {"BookedBy": self.BookedBy, "BookingDate": self.BookingDate}


@dataclass
class Reservation:
    """
    Reservation model.
    """

    CrsConfirmationNumber: str
    status: str
    BookingInfo: dict[str, Any]
    Hotel: dict[str, Any]
    RoomStay: dict[str, Any]
    Guests: list[dict[str, Any]]
    RoomPrices: dict[str, Any]
    Currency: dict[str, Any]
    CreateDateTime: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    UpdateDateTime: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    Brand: dict[str, Any] = field(default_factory=dict)
    Chain: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reservation":
        """Create a Reservation instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert Reservation instance to dictionary."""
        result = {
            "CrsConfirmationNumber": self.CrsConfirmationNumber,
            "status": self.status,
            "CreateDateTime": self.CreateDateTime,
            "UpdateDateTime": self.UpdateDateTime,
            "BookingInfo": self.BookingInfo,
            "Hotel": self.Hotel,
            "RoomStay": self.RoomStay,
            "Guests": self.Guests,
            "RoomPrices": self.RoomPrices,
            "Currency": self.Currency,
        }

        if self.Brand:
            result["Brand"] = self.Brand

        if self.Chain:
            result["Chain"] = self.Chain

        return result


@dataclass
class BookingModel:
    """
    BookingModel for creating reservations.
    """

    BookingInfo: dict[str, Any]
    Hotel: dict[str, Any]
    RoomStay: dict[str, Any]
    Guests: list[dict[str, Any]]
    status: str
    Brand: dict[str, Any] | None = None
    Chain: dict[str, Any] | None = None
    Currency: dict[str, Any] | None = None
    RoomPrices: dict[str, Any] | None = None
    CrsConfirmationNumber: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BookingModel":
        """Create a BookingModel instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert BookingModel instance to dictionary."""
        result = {
            "BookingInfo": self.BookingInfo,
            "Hotel": self.Hotel,
            "RoomStay": self.RoomStay,
            "Guests": self.Guests,
            "status": self.status,
        }

        if self.Brand:
            result["Brand"] = self.Brand

        if self.Chain:
            result["Chain"] = self.Chain

        if self.Currency:
            result["Currency"] = self.Currency

        if self.RoomPrices:
            result["RoomPrices"] = self.RoomPrices

        if self.CrsConfirmationNumber:
            result["CrsConfirmationNumber"] = self.CrsConfirmationNumber

        return result


@dataclass
class UpdateBookingModel:
    """
    UpdateBookingModel for modifying reservations.
    """

    Reservations: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateBookingModel":
        """Create an UpdateBookingModel instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert UpdateBookingModel instance to dictionary."""
        return {"Reservations": self.Reservations}


@dataclass
class CancelModel:
    """
    CancelModel for cancelling reservations.
    """

    Hotel: dict[str, Any]
    CrsConfirmationNumber: str
    CancellationDetails: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CancelModel":
        """Create a CancelModel instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert CancelModel instance to dictionary."""
        result = {"Hotel": self.Hotel, "CrsConfirmationNumber": self.CrsConfirmationNumber}

        if self.CancellationDetails:
            result["CancellationDetails"] = self.CancellationDetails

        return result


@dataclass
class CancelResponseModel:
    """
    CancelResponseModel for cancellation responses.
    """

    CrsCancellationNumber: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CancelResponseModel":
        """Create a CancelResponseModel instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert CancelResponseModel instance to dictionary."""
        return {"CrsCancellationNumber": self.CrsCancellationNumber}


@dataclass
class Pagination:
    """
    Pagination model.
    """

    total: int
    start: int
    size: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Pagination":
        """Create a Pagination instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert Pagination instance to dictionary."""
        return {"total": self.total, "start": self.start, "size": self.size}


@dataclass
class ReservationsModel:
    """
    ReservationsModel for returning multiple reservations.
    """

    pagination: dict[str, int]
    reservations: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReservationsModel":
        """Create a ReservationsModel instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert ReservationsModel instance to dictionary."""
        return {"pagination": self.pagination, "reservations": self.reservations}
