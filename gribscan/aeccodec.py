"""
AEC codec numcodec bindings
"""

import ctypes
import numcodecs
from numcodecs.compat import ensure_contiguous_ndarray

aec = ctypes.CDLL("libaec.so")

class aec_stream(ctypes.Structure):
    _fields_ = [("next_in", ctypes.c_char_p),
                ("avail_in", ctypes.c_size_t),
                ("total_in", ctypes.c_size_t),
                ("next_out", ctypes.c_char_p),
                ("avail_out", ctypes.c_size_t),
                ("total_out", ctypes.c_size_t),
                ("bits_per_sample", ctypes.c_uint),
                ("block_size", ctypes.c_uint),
                ("rsi", ctypes.c_uint),
                ("flags", ctypes.c_uint),
                ("internal_state", ctypes.c_char_p),
               ]

aec_stream_p = ctypes.POINTER(aec_stream)

AEC_DATA_SIGNED = 1
AEC_DATA_3BYTE = 2
AEC_DATA_MSB = 4
AEC_DATA_PREPROCESS = 8
AEC_RESTRICTED = 16
AEC_PAD_RSI = 32
AEC_NOT_ENFORCE = 64

AEC_OK = 0
AEC_CONF_ERROR = -1
AEC_STREAM_ERROR = -2
AEC_DATA_ERROR = -3
AEC_MEM_ERROR = -4

AEC_NO_FLUSH = 0
AEC_FLUSH = 1

aec.aec_encode_init.argtypes = [aec_stream_p]
aec.aec_encode_init.restype = ctypes.c_int

aec.aec_encode.argtypes = [aec_stream_p, ctypes.c_int]  # stream, flush
aec.aec_encode.restype = ctypes.c_int

aec.aec_encode_end.argtypes = [aec_stream_p]
aec.aec_encode_end.restype = ctypes.c_int


aec.aec_decode_init.argtypes = [aec_stream_p]
aec.aec_decode_init.restype = ctypes.c_int

aec.aec_decode.argtypes = [aec_stream_p, ctypes.c_int]  # stream, flush
aec.aec_decode.restype = ctypes.c_int

aec.aec_decode_end.argtypes = [aec_stream_p]
aec.aec_decode_end.restype = ctypes.c_int


aec.aec_buffer_encode.argtypes = [aec_stream_p]
aec.aec_buffer_encode.restype = ctypes.c_int

aec.aec_buffer_decode.argtypes = [aec_stream_p]
aec.aec_buffer_decode.restype = ctypes.c_int


# defaults from aec binary
#    strm.bits_per_sample = 8;
#    strm.block_size = 8;
#    strm.rsi = 2;
#    strm.flags = AEC_DATA_PREPROCESS;


decode_chunksize = 10000000

class AECCodec(numcodecs.abc.Codec):
    codec_id = "aec"
    
    def __init__(self, bits_per_sample=8, block_size=8, rsi=2, preprocess=True):
        self.bits_per_sample = bits_per_sample
        self.block_size = block_size
        self.rsi = rsi
        self.preprocess = preprocess
        
    
    def get_config(self):
        return {
            "id": codec_id,
            "bits_per_sample": self.bits_per_sample,
            "block_size": self.block_size,
            "rsi": self.rsi,
            "preprocess": self.preprocess,
        }
    
    @classmethod
    def from_config(cls, config):
        return cls(**{k: v for k, b in config.items() if k != "id"})

    def encode(self, buf):
        buf = ensure_contiguous_ndarray(buf)
        strm = aec_stream()
        strm.bits_per_sample = self.bits_per_sample
        strm.block_size = self.block_size
        strm.rsi = self.rsi
        if self.preprocess:
            strm.flags = AEC_DATA_PREPROCESS

        strm.next_in = buf.ctypes.data_as(ctypes.c_char_p)
        strm.avail_in = buf.size * buf.itemsize

        out = ctypes.create_string_buffer(2 * buf.size * buf.itemsize)
        strm.next_out = ctypes.cast(out, ctypes.c_char_p)
        strm.avail_out = len(out)

        if aec.aec_encode_init(strm) != AEC_OK:
            raise ValueError("could not initialize AEC encoder")

        if aec.aec_encode(strm, AEC_FLUSH) != AEC_OK:
            raise ValueError("could not encode")

        aec.aec_encode_end(strm)

        return bytes(out[:strm.total_out])

    def decode(self, buf, out=None):
        buf = ensure_contiguous_ndarray(buf)
        strm = aec_stream()
        strm.bits_per_sample = self.bits_per_sample
        strm.block_size = self.block_size
        strm.rsi = self.rsi
        if self.preprocess:
            strm.flags = AEC_DATA_PREPROCESS

        strm.next_in = buf.ctypes.data_as(ctypes.c_char_p)
        strm.avail_in = buf.size * buf.itemsize
        
        if out is not None:
            strm.next_out = out.ctypes.data_as(ctypes.c_char_p)
            strm.avail_out = out.size * out.itemsize
        else:
            out_buffer = ctypes.create_string_buffer(decode_chunksize)
            strm.next_out = ctypes.cast(out_buffer, ctypes.c_char_p)
            strm.avail_out = decode_chunksize
            outlist = []

        if aec.aec_decode_init(strm) != AEC_OK:
            raise ValueError("could not initialize AEC decoder")
        
        if out is not None:
            if aec.aec_decode(strm, AEC_FLUSH) != AEC_OK:
                raise ValueError("could not decode")
        else:
            total_out = 0
            more_data = True
            while more_data:
                if aec.aec_decode(strm, AEC_NO_FLUSH) != AEC_OK:
                    raise ValueError("could not decode")

                if strm.total_out - total_out > 0:
                    outlist.append(bytes(out_buffer[:strm.total_out - total_out]))
                    total_out = strm.total_out
                    strm.next_out = ctypes.cast(out_buffer, ctypes.c_char_p)
                    strm.avail_out = decode_chunksize
                else:
                    more_data = False

        aec.aec_decode_end(strm)

        if out is not None:
            return out
        else:
            return b''.join(outlist)
