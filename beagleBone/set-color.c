/** \file
 * Test the ledscape library by pulsing RGB on the first three LEDS.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <inttypes.h>
#include <errno.h>
#include <unistd.h>
#include <sys/time.h>
#include "ledscape.h"

#ifndef LEDSCAPE_NUM_LEDS
#define LEDSCAPE_NUM_LEDS 1009
#endif

int main (int argc, char *argv[])
{
	ledscape_t * const leds = ledscape_init_with_programs(LEDSCAPE_NUM_LEDS,"pru/bin/ws281x-valhalla-pru0.bin","pru/bin/ws281x-valhalla-pru1.bin");
	uint8_t rgb[3];
	if ( argc > 4 ) {
		rgb[0] = atoi(argv[1]);
		rgb[1] = atoi(argv[2]);
		rgb[2] = atoi(argv[3]);
	} else {
		printf("Provide at least 3 colors!\n");
		exit(1);
	}
	
	printf("here\n");
	ledscape_frame_t * const frame = ledscape_frame(leds, 0);
	if ( argc > 4 ) {
		unsigned strip_input = atoi(argv[4]);
		printf("Using strip %i.\n", strip_input);
		for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS; p++)
		{
			ledscape_set_color(frame, COLOR_ORDER_RGB, strip_input, p, rgb[0] , rgb[1], rgb[2]);
		}
	} else {
		printf("Using all strips.\n");
		for (unsigned strip = 0 ; strip < LEDSCAPE_NUM_STRIPS ; strip++)
		{
			for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS; p++)
			{
				ledscape_set_color(frame, COLOR_ORDER_RGB, strip, p, rgb[0] , rgb[1], rgb[2]);
			}
		}
	}
	ledscape_wait(leds);
	ledscape_draw(leds, 0);

	//ledscape_close(leds);

	return EXIT_SUCCESS;
}