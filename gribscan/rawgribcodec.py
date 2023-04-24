import eccodes
import numcodecs
from numcodecs.compat import ndarray_copy, ensure_contiguous_ndarray


class RawGribCodec(numcodecs.abc.Codec):
    codec_id = "gribscan.rawgrib"

    def encode(self, buf):
        return buf

    def decode(self, buf, out=None):
        mid = eccodes.codes_new_from_message(bytes(buf))
        try:
            data = eccodes.codes_get_array(mid, "values")
        finally:
            eccodes.codes_release(mid)

        if hasattr(data, "build_array"):
            data = data.build_array()

        if out is not None:
            return ndarray_copy(data, out)
        else:
            return data
