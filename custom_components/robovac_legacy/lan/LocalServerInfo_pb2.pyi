from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LocalServerMessage(_message.Message):
    __slots__ = ("magic_num", "localcode", "a", "b", "c", "d")
    class PingPacketMessage(_message.Message):
        __slots__ = ("type",)
        class PingPacketType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            PING_REQUEST: _ClassVar[LocalServerMessage.PingPacketMessage.PingPacketType]
            PING_RESPONSE: _ClassVar[LocalServerMessage.PingPacketMessage.PingPacketType]
        PING_REQUEST: LocalServerMessage.PingPacketMessage.PingPacketType
        PING_RESPONSE: LocalServerMessage.PingPacketMessage.PingPacketType
        TYPE_FIELD_NUMBER: _ClassVar[int]
        type: LocalServerMessage.PingPacketMessage.PingPacketType
        def __init__(self, type: _Optional[_Union[LocalServerMessage.PingPacketMessage.PingPacketType, str]] = ...) -> None: ...
    class OtaPacketMessage(_message.Message):
        __slots__ = ("type", "otafile_size", "ota_data", "cause")
        class OtaPacketType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            REQUEST_UPDATE_FIRMWARE: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
            PERMIT_UPDATE: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
            OTA_UPDATE_DATA_SEND: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
            UPDATE_DATA_VERIFY: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
            OTA_UPDATE_ABORT: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
            OTA_COMPLETE_NOTIFY: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
            OTA_STATUS_FAILD: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
            OTA_STATUS_SUCCESS: _ClassVar[LocalServerMessage.OtaPacketMessage.OtaPacketType]
        REQUEST_UPDATE_FIRMWARE: LocalServerMessage.OtaPacketMessage.OtaPacketType
        PERMIT_UPDATE: LocalServerMessage.OtaPacketMessage.OtaPacketType
        OTA_UPDATE_DATA_SEND: LocalServerMessage.OtaPacketMessage.OtaPacketType
        UPDATE_DATA_VERIFY: LocalServerMessage.OtaPacketMessage.OtaPacketType
        OTA_UPDATE_ABORT: LocalServerMessage.OtaPacketMessage.OtaPacketType
        OTA_COMPLETE_NOTIFY: LocalServerMessage.OtaPacketMessage.OtaPacketType
        OTA_STATUS_FAILD: LocalServerMessage.OtaPacketMessage.OtaPacketType
        OTA_STATUS_SUCCESS: LocalServerMessage.OtaPacketMessage.OtaPacketType
        class FailCause(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ERASE_SECTION_FAILD: _ClassVar[LocalServerMessage.OtaPacketMessage.FailCause]
            DATA_OFFSET_ERROR: _ClassVar[LocalServerMessage.OtaPacketMessage.FailCause]
            SWITCH_SIGN_FAILD: _ClassVar[LocalServerMessage.OtaPacketMessage.FailCause]
            BRUN_UNFINISHED_ERROR: _ClassVar[LocalServerMessage.OtaPacketMessage.FailCause]
        ERASE_SECTION_FAILD: LocalServerMessage.OtaPacketMessage.FailCause
        DATA_OFFSET_ERROR: LocalServerMessage.OtaPacketMessage.FailCause
        SWITCH_SIGN_FAILD: LocalServerMessage.OtaPacketMessage.FailCause
        BRUN_UNFINISHED_ERROR: LocalServerMessage.OtaPacketMessage.FailCause
        class OtaUpdateDataMessage(_message.Message):
            __slots__ = ("adr_offset", "packet_length", "data")
            ADR_OFFSET_FIELD_NUMBER: _ClassVar[int]
            PACKET_LENGTH_FIELD_NUMBER: _ClassVar[int]
            DATA_FIELD_NUMBER: _ClassVar[int]
            adr_offset: int
            packet_length: int
            data: bytes
            def __init__(self, adr_offset: _Optional[int] = ..., packet_length: _Optional[int] = ..., data: _Optional[bytes] = ...) -> None: ...
        TYPE_FIELD_NUMBER: _ClassVar[int]
        OTAFILE_SIZE_FIELD_NUMBER: _ClassVar[int]
        OTA_DATA_FIELD_NUMBER: _ClassVar[int]
        CAUSE_FIELD_NUMBER: _ClassVar[int]
        type: LocalServerMessage.OtaPacketMessage.OtaPacketType
        otafile_size: int
        ota_data: LocalServerMessage.OtaPacketMessage.OtaUpdateDataMessage
        cause: LocalServerMessage.OtaPacketMessage.FailCause
        def __init__(self, type: _Optional[_Union[LocalServerMessage.OtaPacketMessage.OtaPacketType, str]] = ..., otafile_size: _Optional[int] = ..., ota_data: _Optional[_Union[LocalServerMessage.OtaPacketMessage.OtaUpdateDataMessage, _Mapping]] = ..., cause: _Optional[_Union[LocalServerMessage.OtaPacketMessage.FailCause, str]] = ...) -> None: ...
    class UserDataMessage(_message.Message):
        __slots__ = ("type", "usr_data")
        class UserDataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            sendUsrDataToDev: _ClassVar[LocalServerMessage.UserDataMessage.UserDataType]
            getDevStatusData: _ClassVar[LocalServerMessage.UserDataMessage.UserDataType]
            sendStausDataToApp: _ClassVar[LocalServerMessage.UserDataMessage.UserDataType]
        sendUsrDataToDev: LocalServerMessage.UserDataMessage.UserDataType
        getDevStatusData: LocalServerMessage.UserDataMessage.UserDataType
        sendStausDataToApp: LocalServerMessage.UserDataMessage.UserDataType
        TYPE_FIELD_NUMBER: _ClassVar[int]
        USR_DATA_FIELD_NUMBER: _ClassVar[int]
        type: LocalServerMessage.UserDataMessage.UserDataType
        usr_data: bytes
        def __init__(self, type: _Optional[_Union[LocalServerMessage.UserDataMessage.UserDataType, str]] = ..., usr_data: _Optional[bytes] = ...) -> None: ...
    class DevinfoMessage(_message.Message):
        __slots__ = ("type", "data")
        class DevInfoType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            REQUEST_KEYCODE: _ClassVar[LocalServerMessage.DevinfoMessage.DevInfoType]
            RESPONSE_KEYCODE: _ClassVar[LocalServerMessage.DevinfoMessage.DevInfoType]
        REQUEST_KEYCODE: LocalServerMessage.DevinfoMessage.DevInfoType
        RESPONSE_KEYCODE: LocalServerMessage.DevinfoMessage.DevInfoType
        TYPE_FIELD_NUMBER: _ClassVar[int]
        DATA_FIELD_NUMBER: _ClassVar[int]
        type: LocalServerMessage.DevinfoMessage.DevInfoType
        data: bytes
        def __init__(self, type: _Optional[_Union[LocalServerMessage.DevinfoMessage.DevInfoType, str]] = ..., data: _Optional[bytes] = ...) -> None: ...
    MAGIC_NUM_FIELD_NUMBER: _ClassVar[int]
    LOCALCODE_FIELD_NUMBER: _ClassVar[int]
    A_FIELD_NUMBER: _ClassVar[int]
    B_FIELD_NUMBER: _ClassVar[int]
    C_FIELD_NUMBER: _ClassVar[int]
    D_FIELD_NUMBER: _ClassVar[int]
    magic_num: int
    localcode: str
    a: LocalServerMessage.PingPacketMessage
    b: LocalServerMessage.OtaPacketMessage
    c: LocalServerMessage.UserDataMessage
    d: LocalServerMessage.DevinfoMessage
    def __init__(self, magic_num: _Optional[int] = ..., localcode: _Optional[str] = ..., a: _Optional[_Union[LocalServerMessage.PingPacketMessage, _Mapping]] = ..., b: _Optional[_Union[LocalServerMessage.OtaPacketMessage, _Mapping]] = ..., c: _Optional[_Union[LocalServerMessage.UserDataMessage, _Mapping]] = ..., d: _Optional[_Union[LocalServerMessage.DevinfoMessage, _Mapping]] = ...) -> None: ...
