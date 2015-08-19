Note: git revision is currently 1c3bc60

Copy valhalla-dces.c to LEDscape.
Copy valhalla.json to pru/mappings
Copy service?

Add valhalla-dces to Makefile targets:

TARGETS += valhalla-dces

change number of strips to 8 in ledscape.h 

#define LEDSCAPE_NUM_STRIPS

optionally add number of pixels as well (if used in other files)

#define LEDSCAPE_NUM_PIXELS 1009

Change prus to support 8 strips, rather than 48. Line 174 of pru/templates/ replace 48 with 8.

optional

echo -ne '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' | nc -p 5252 localhost

make service
cp valhalla.service /etc/systemd/system/
systemctl enable /etc/systemd/system/valhalla.service
systemctl start valhalla.service

also handy:  systemctl daemon-reload (to reload changes to the service)


modify LEDscape gpios!!!!


static const uint8_t gpios0[] = {2,7,14};

static const uint8_t gpios1[] = {18,19,28};

static const uint8_t gpios2[] = {};

static const uint8_t gpios3[] = {16, 17};
