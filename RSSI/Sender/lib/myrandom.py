import crypto
import uos


def Random():
   r = crypto.getrandbits(32)
   return ((r[0]<<24)+(r[1]<<16)+(r[2]<<8)+r[3])/4294967295.0

def RandomRange(rfrom, rto):
   return Random()*(rto-rfrom)+rfrom

def RandomInt(rto):
    return uos.urandom(1)[0] % rto
