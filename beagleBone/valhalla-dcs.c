/** 
 * Valhalla Dual Color Server (DCS).
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
#define STRIP_FL		0 //6 //wtf?  It looks like both FL and BL are controlled by 7... are they shorted?
#define STRIP_BL		7

void draw_sc(ledscape_frame_t * frame, LED_settings * leds) {
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) {
			for (unsigned strip = 0 ; strip < LEDSCAPE_NUM_STRIPS ; strip++) {
					ledscape_set_color(frame, strip, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
			}
	}
} 

void draw_split_lr(ledscape_frame_t * frame, LED_settings * leds) {
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_FL, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_BL, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_FR, p, leds->rgb2[0], leds->rgb2[1], leds->rgb2[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_BR, p, leds->rgb2[0], leds->rgb2[1], leds->rgb2[2]);
} 

void draw_split_fb(ledscape_frame_t * frame, LED_settings * leds) {
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_FL, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_FR, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_BL, p, leds->rgb2[0], leds->rgb2[1], leds->rgb2[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_BR, p, leds->rgb2[0], leds->rgb2[1], leds->rgb2[2]);
} 

void draw_split_op(ledscape_frame_t * frame, LED_settings * leds) {
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_FL, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_BR, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_FR, p, leds->rgb2[0], leds->rgb2[1], leds->rgb2[2]);
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) 
		ledscape_set_color(frame, STRIP_BL, p, leds->rgb2[0], leds->rgb2[1], leds->rgb2[2]);
} 

void draw_interleave(ledscape_frame_t * frame, LED_settings * leds) {
	//unsigned len = leds->mods[0]*2;
        if (leds->mods[0] < 1) //important, other there is a FP exception
		leds->mods[0] = 1;
	unsigned len = leds->mods[0]*2;

	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) {
			for (unsigned strip = 0 ; strip < LEDSCAPE_NUM_STRIPS ; strip++) {
					if ( (p % len) < leds->mods[0])
						ledscape_set_color(frame, strip, p, leds->rgb1[0], leds->rgb1[1], leds->rgb1[2]);
					else
						ledscape_set_color(frame, strip, p, leds->rgb2[0], leds->rgb2[1], leds->rgb2[2]);
			}
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
			//printf("Received Packet. Mode: %i Setting[0]: %i, R1: %i G1: %i B1: %i, R2: %i G2: %i B2: %i\n", leds.mode, leds.mods[0], leds.rgb1[0], leds.rgb1[1], leds.rgb1[2], leds.rgb2[0], leds.rgb2[1], leds.rgb2[2]);
			
			// Alternate frame buffers on each draw command
			const unsigned frame_num = i++ % 2;
			ledscape_frame_t * const frame = ledscape_frame(scape, frame_num); //get frame
			
			switch (leds.mode) {
				case SINGLE_COLOR:
					draw_sc(frame, &leds);
					break;
				case SPLIT_LR:
					draw_split_lr(frame, &leds);
					break;
				case SPLIT_FB:
					draw_split_fb(frame, &leds);
					break;
				case SPLIT_OP:
					draw_split_op(frame, &leds);
					break;
				case INTERLEAVE:
					draw_interleave(frame, &leds);
					break;
				default:
					printf("Unkown/unimplemented mode %d.\n", leds.mode);
			}		
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
