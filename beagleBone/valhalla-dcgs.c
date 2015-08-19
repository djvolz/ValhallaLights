/** 
 * Valhalla Dual Color Gradient Server (DCGS).
 * Take a 10 byte UDP packet on the LED_PORT, parse out the mode, settings, and two colors,
 * then write it to all of the strips accordingly.
 * Note that this is realtime, so it will drop packets so that the response is instantaneous.
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
#include <netdb.h>
#include <netinet/in.h>
#include <sys/uio.h>

#define LED_PORT 5252
#define BUF_SIZE 1024

//format for packet
typedef struct t_LED_settings{
	char mode;
	char mods[3];
	char rgb1[3];
	char rgb2[3];
}LED_settings;

#define SINGLE_COLOR 		0
#define SPLIT_LR		1
#define SPLIT_FB		2
#define SPLIT_OP		3
#define INTERLEAVE		4

#define STRIP_FR		0
#define STRIP_BR		2
#define STRIP_FL		6 
#define STRIP_BL		7
/*
void draw2(ledscape_frame_t * frame, char * rgb, int len, int offset) {
	int idx, idx2;
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) {
		idx = (offset + p) % len;
		ledscape_set_color(frame, STRIP_FL, p, rgb[idx][0], rgb[idx][1], rgb[idx][2]);
		ledscape_set_color(frame, STRIP_BL, p, rgb[idx][0], rgb[idx][1], rgb[idx][2]);
		
		idx2 = (offset - p) % len; //these strips are oriented opposite of the others...
		ledscape_set_color(frame, STRIP_FR, p, rgb[idx2][0], rgb[idx2][1], rgb[idx2][2]);
		ledscape_set_color(frame, STRIP_BR, p, rgb[idx2][0], rgb[idx2][1], rgb[idx2][2]);
	}
} */

//Think of this as starting clockwise from the back left strip.
void draw(ledscape_frame_t * frame, char rgb[4100][3], int len, int offset) {
	printf("called draw() with len %d and offset %d.\n", len, offset);
	int idx;
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) {
		idx = (offset + p) % len;  //start at the beginning (plus offset)
		ledscape_set_color(frame, STRIP_BL, p, rgb[idx][0], rgb[idx][1], rgb[idx][2]);
		
		idx = (offset + p + LEDSCAPE_NUM_LEDS) % len; //start at the end of the last strip, plus offset
		ledscape_set_color(frame, STRIP_FL, p, rgb[idx][0], rgb[idx][1], rgb[idx][2]);
		
		//these two strips are oriented opposite of the other two, so we use LEDSCAPE_NUM_LEDS - p for the index to reverse the drawing.
		
		idx = (offset + p + 2*LEDSCAPE_NUM_LEDS) % len; //start at the end of the last strip, plus offset
		ledscape_set_color(frame, STRIP_FR, LEDSCAPE_NUM_LEDS - p, rgb[idx][0], rgb[idx][1], rgb[idx][2]);
		
		idx = (len + offset - p  - 1) % len; // let's make sure this side is smooth (since we don't have exact LED counts), so we flip it rather than add 3*LEDSCAPE_NUM_LEDs //stupid modulus operator can be negative.
		ledscape_set_color(frame, STRIP_BR, p, rgb[idx][0], rgb[idx][1], rgb[idx][2]);
	}
}


//TODO: trap sigint and close socket and leds.
int main (int argc, char *argv[])
{
    //**************** Initialize Socket ***************//
	char message[BUF_SIZE];
	char r, g, b;
	char newdata = 0;
	int sock;
	struct sockaddr_in name;
	struct hostent *gethostbyname();
	int num_bytes;
	unsigned i = 0;
	LED_settings leds;
	
	printf("Listen activating.\n");

	/* Create socket from which to read */
	sock = socket(AF_INET, SOCK_DGRAM, 0);
	//sock = socket(AF_INET , SOCK_RAW , IPPROTO_UDP);
	if (sock < 0)   {
	perror("Opening datagram socket");
	exit(1);
	}

	/* Bind our local address so that the client can send to us */
	bzero((char *) &name, sizeof(name));
	name.sin_family = AF_INET;
	name.sin_addr.s_addr = htonl(INADDR_ANY);
	name.sin_port = htons(LED_PORT);

	if (bind(sock, (struct sockaddr *) &name, sizeof(name))) {
		perror("binding datagram socket");
		exit(1);
	}

	printf("Socket has port number #%d\n", ntohs(name.sin_port));
  
	//**************** Initialize LEDscape ***************//
	ledscape_t * const scape = ledscape_init(LEDSCAPE_NUM_LEDS);


	while (1) {
		//clear out the receive buffer, since it contains outdated frames, but be sure to save the last value
		while (num_bytes > 0) {
			//num_bytes = recv(sock, message, BUF_SIZE, MSG_DONTWAIT);
			num_bytes = recv(sock, (char *) &leds, sizeof(LED_settings), MSG_DONTWAIT);
			if (num_bytes >= sizeof(LED_settings)) 
				newdata = 1;
			else
				printf("Warning! Received bad packet -- too short. %d\n", num_bytes);
		}
		//if we haven't gotten anything new, let's block.
		if (!newdata) {
			//if ((num_bytes = read(sock, message, BUF_SIZE)) > 2) {
			if ((num_bytes = read(sock, (char *) &leds, sizeof(LED_settings))) >=  sizeof(LED_settings) ) 
				newdata = 1;
			else
				printf("Warning! Received bad packet -- too short. %d\n", num_bytes);
		}
		if (newdata) {
			newdata = 0;
			printf("Received Packet. Mode: %i Setting[0]: %i, R1: %i G1: %i B1: %i, R2: %i G2: %i B2: %i\n", leds.mode, leds.mods[0], leds.rgb1[0], leds.rgb1[1], leds.rgb1[2], leds.rgb2[0], leds.rgb2[1], leds.rgb2[2]);
			
			// Alternate frame buffers on each draw command
			const unsigned frame_num = i++ % 2;
			ledscape_frame_t * const frame = ledscape_frame(scape, frame_num); //get frame
			
			//we want to be able to control the colors up to making them 2040 long, but are only sent a max of 254, so we have to scale them up.
			//Note that this normalizes them to 1008, but then we double them when they are mirrored below.
			//have to cast to int first...
			int color_len = ( (leds.mods[0]*leds.mods[0]) >> 5 ); //should always have at least one color
			int grad_len = (leds.mods[1] > leds.mods[0]) ? color_len : ( (leds.mods[1]*leds.mods[1])  >> 5 ); // grad_len can't be bigger than color_len
			int offset = ( (leds.mods[2]*leds.mods[2])  >> 6 );  //rotate the colors across the strips (e.g. a color length of 2020 and no rotation makes the colors LR, a rotation of 1010 would make them FB, where as a color length of 1010 would make them offset.)
			
			color_len = (color_len > 950 && color_len < 1070) ? 1009 : color_len; //make the half-way point "sticky"
			//offset = (offset > 480 && offset < 530) ? 504 : offset; //make the half-way point "sticky"
			
			offset -= grad_len / 2;  //keep the colors centered while adjusting the gradient.
			
			printf("building gradient with color_len %d, grad_len %d, and offset %d.\n", color_len, grad_len, offset);
			
			int idx = 0;
			char rgb[4100][3]; //char out[LEDSCAPE_NUM_LEDS*2][3];
			for (int j = 0; j <= (color_len - grad_len); j++) {
				rgb[idx][0] =  leds.rgb1[0];
				rgb[idx][1] =  leds.rgb1[1];
				rgb[idx++][2] =  leds.rgb1[2];
			}
			float grad_step[3]; //
			if ( grad_len > 0 ) {
				for (int j = 0; j < 3; j++) {
					grad_step[j] = ((float)leds.rgb2[j] - (float)leds.rgb1[j])/(grad_len);
				}			
				for (int j = 1; j < grad_len + 1; j++) { //the end points are always the same as rgb1 and rgb2
					rgb[idx][0] =  leds.rgb1[0] + grad_step[0]*j;
					rgb[idx][1] =  leds.rgb1[1] + grad_step[1]*j;
					rgb[idx++][2] =  leds.rgb1[2] + grad_step[2]*j;
				}
			}
			for (int j = 0; j <= (color_len - grad_len); j++) {
				rgb[idx][0] =  leds.rgb2[0];
				rgb[idx][1] =  leds.rgb2[1];
				rgb[idx++][2] =  leds.rgb2[2];
			}
			if ( grad_len > 0 ) {
				for (int j = 1; j < grad_len + 1; j++) { //the end points are always the same as rgb1 and rgb2
					rgb[idx][0] =  leds.rgb2[0] - grad_step[0]*j;
					rgb[idx][1] =  leds.rgb2[1] - grad_step[1]*j;
					rgb[idx++][2] =  leds.rgb2[2] - grad_step[2]*j;
				}			
			}
			//for (int j = idx-2; j > 0; j--) { //mirror it to make it smooth, snip off the first and last pixels so they aren't duplicated
			/*for (int j = idx-1; j >= 0; j--) {
				rgb[idx][0] =  rgb[j][0];
				rgb[idx][1] =  rgb[j][1];
				rgb[idx++][2] =  rgb[j][2];
			}*/
			
			draw(frame, rgb, idx, offset);
			
			const uint32_t response = ledscape_wait(scape);
			ledscape_draw(scape, frame_num);
		}
		else
			printf("Waiting for ethernet...\n");  //while the socket read is blocking, it does eventually timeout

	}
    close(sock);
//	ledscape_close(leds); //clay: for some reason this segfaults...

	return EXIT_SUCCESS;
}
