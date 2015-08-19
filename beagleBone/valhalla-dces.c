/** 
 * Valhalla Dual Color Effect Server (DCES).
 * Take a 16 byte UDP packet on the LED_PORT, parse out the mode, settings, and two colors,
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

//so we don't have to modify ledscape.h
#ifndef LEDSCAPE_NUM_LEDS
#define LEDSCAPE_NUM_LEDS 1008
#endif

#define NUM_COLORS		3  //we only support up to three colors now anyway... but may be useful in the future

#define STRIP_FR		3
#define STRIP_BR		7
#define STRIP_FL		2 
#define STRIP_BL		4

//use enum for this...
#define MODE_STATIC		0
#define MODE_PULSING	1
#define MODE_ROTATING	2
#define MODE_SWAYING	4
#define MODE_THIRDCOLOR 8  //three colors or two colors...
#define MODE_MUSIC		16 //TODO: Implement this.  Probably requires another socket

//format for packet
typedef struct t_LED_settings{
	char mode;
	char mods[6];		//color_length, gradient_length, offset (or sway distance), offset_speed, pulse intensity, pulse speed, 
	char rgb[NUM_COLORS][3];		//three colors, each with rgb. //last color is optional, and enabled by the MODE_THIRDCOLOR
} LED_settings;

//Think of this as starting clockwise from the back left strip.
//Weird bug... RGB does not draw rgb, it does BRG... GBR works.
void draw(ledscape_frame_t * frame, char rgb[][3], int len, int offset) {
	//printf("called draw() with len %d and offset %d.\n", len, offset);
	int idx;
	for (unsigned p = 0 ; p < LEDSCAPE_NUM_LEDS ; p++) {
		idx = (offset + p) % len;  //start at the beginning (plus offset)
		ledscape_set_color(frame, COLOR_ORDER_GBR, STRIP_BL, p, rgb[idx][1], rgb[idx][2], rgb[idx][0]);
		
		idx = (offset + p + LEDSCAPE_NUM_LEDS) % len; //start at the end of the last strip, plus offset
		ledscape_set_color(frame, COLOR_ORDER_GBR, STRIP_FL, p, rgb[idx][1], rgb[idx][2], rgb[idx][0]);
		
		//these two strips are oriented opposite of the other two, so we use LEDSCAPE_NUM_LEDS - p for the index to reverse the drawing.
		
		idx = (offset + p + 2*LEDSCAPE_NUM_LEDS) % len; //start at the end of the last strip, plus offset
		ledscape_set_color(frame, COLOR_ORDER_GBR, STRIP_FR, LEDSCAPE_NUM_LEDS - p, rgb[idx][1], rgb[idx][2], rgb[idx][0]);
		
		idx = (16*len + offset - p  - 1) % len; // let's make sure this side is smooth (since we don't have exact LED counts), so we flip it rather than add 3*LEDSCAPE_NUM_LEDs //stupid modulus operator can be negative.
		ledscape_set_color(frame, COLOR_ORDER_GBR, STRIP_BR, p, rgb[idx][1], rgb[idx][2], rgb[idx][0]);
	}
}


//TODO: trap sigint and close socket and leds.
int main (int argc, char *argv[]) {
	char newdata = 0;
	char num_colors = 2;
	struct sockaddr_in name;
	struct hostent *gethostbyname();
	LED_settings leds, leds_orig = {0};
	int sock, num_bytes, color_len, grad_len, idx, j, c, t, p, fi, pulse_sign, offset_sign = 0;  //use t for the rgb color tuplet
	float offset, pulse = 0;
	float grad_step[NUM_COLORS][3];
	char rgb[6150][3]; //char out[LEDSCAPE_NUM_LEDS*2][3]; //4100, third color needs more...LEDSCAPE_NUM_LEDS*6+
	struct timeval tv, tv_last, tv_draw;
	gettimeofday(&tv_last, NULL);

	//bzero(&leds, sizeof(LED_settings)); //doesn't matter, overwritten.
	//bzero(&leds_orig, sizeof(LED_settings));
	//**************** Initialize Socket ***************//
	printf("Listen activating.\n");

	/* Create socket from which to read */
	sock = socket(AF_INET, SOCK_DGRAM, 0);
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
		perror("Binding datagram socket");
		exit(1);
	}

	printf("Socket has port number #%d\n", ntohs(name.sin_port));
  
	//**************** Initialize LEDscape ***************//
	ledscape_t * const scape = ledscape_init_with_programs(LEDSCAPE_NUM_LEDS,"pru/bin/ws281x-valhalla-pru0.bin","pru/bin/ws281x-valhalla-pru1.bin");

	//main loop
	while (1) {
		//clear out the receive buffer, since it contains outdated frames, but be sure to save the last value
		while (	(num_bytes = recv(sock, (char *) &leds, sizeof(LED_settings), MSG_DONTWAIT)) > 0 ) {
			if (num_bytes >= sizeof(LED_settings)) {
				newdata = 1;
				leds_orig = leds;
			}
			else
				printf("Warning! Received bad packet -- too short. %d\n", num_bytes);
		}
		
		//if we haven't gotten anything new, and we aren't doing any effects, let's block (no MSG_DONTWAIT).
		if (!newdata && ( leds.mode == MODE_STATIC || leds.mode == MODE_THIRDCOLOR ) ) {
			//if ((num_bytes = read(sock, message, BUF_SIZE)) > 2) {
			if ((num_bytes = read(sock, (char *) &leds, sizeof(LED_settings))) >=  sizeof(LED_settings) ) {
				newdata = 1;
				leds_orig = leds;
			}
			else
				printf("Warning! Received bad packet -- too short. %d\n", num_bytes);
		}
		else { //we received a new setting, or are doing a realtime effect, so we need to update the LEDs.
		
			if (newdata) {
				//if (leds.mode != leds_orig.mode && (leds.mode == MODE_SWAYING || leds.mode == MODE_SWAYPULSE))  //actually this is a cool effect, let's leave it.
				//	offset = 0;				
				//printf("Received Packet. Mode: %i Setting[0]: %i, R1: %i G1: %i B1: %i, R2: %i G2: %i B2: %i\n", leds.mode, leds.mods[0], leds.rgb[0][0], leds.rgb[0][1], leds.rgb[0][2], leds.rgb[1][0], leds.rgb[1][1], leds.rgb[1][2]);
				//printf("Received Packet. Mode: %i, Setting[0]: %i, Setting[1]: %i, Setting[2]: %i, Setting[3]: %i, Setting[4]: %i, Setting[5]: %i, R1: %i G1: %i B1: %i, R2: %i G2: %i B2: %i\n", leds.mode, leds.mods[0], leds.mods[1], leds.mods[2], leds.mods[3], leds.mods[4], leds.mods[5], leds.rgb[0][0], leds.rgb[0][1], leds.rgb[0][2], leds.rgb[1][0], leds.rgb[1][1], leds.rgb[1][2]); //don't print out unless the settings actually changed
				leds = leds_orig; //we copy a good socket read in to leds_orig, so leds_orig is always the latest good socket read.  copy it back over to leds if there was a good socket read, just in case there is a bad socket read. we save the orig for effects baseline	
			}
			newdata = 0;
			
			// Alternate frame buffers on each draw command (double buffer)
			const unsigned frame_num = fi++ % 2;
			ledscape_frame_t * const frame = ledscape_frame(scape, frame_num); //get frame
			
			//we want to be able to control the colors up to making them 2040 long, but are only sent a max of 254, so we have to scale them up.
			//Note that this normalizes them to 2016, which is enough to fill one full side
			color_len = ( (leds.mods[0]*leds.mods[0]) >> 5 );  //0 still means 1 pixel in the for loop //length of one of the colors.
			color_len = (color_len > LEDSCAPE_NUM_LEDS - 65 && color_len < LEDSCAPE_NUM_LEDS + 65) ? LEDSCAPE_NUM_LEDS : color_len; //make the half-way point "sticky" (helpful for doing the same color on opposite sides of the bar)
			grad_len = (leds.mods[1] > leds.mods[0]) ? color_len : ( (leds.mods[1]*leds.mods[1])  >> 5 ); // grad_len can't be bigger than color_len
			/****** DO MOVING EFFECTS *****/
			if (leds.mode & MODE_ROTATING) {
				offset += ( (leds.mods[3] - 127.0) / 4.0); // rotate either direction
			} else if (leds.mode & MODE_SWAYING) {
				offset = (offset_sign) ? offset - (( ( leds.mods[3] + 1.0) / 8)) : (offset + ( ( leds.mods[3] + 1.0) / 8));
				if (offset > leds.mods[2])  //reverse direction high
					offset_sign = 1;
				else if (offset < 0) //reverse direction low
					offset_sign = 0;
			} else {
				offset = ( (leds.mods[2]*leds.mods[2]) >> 6 ) - grad_len / 2;  //rotate the colors across the strips (e.g. a color length of 2016 and no rotation makes the colors LR, a rotation of 1008 would make them FB, where as a color length of 1008 would make them offset
			}
			
			if (leds.mode & MODE_PULSING) {
				pulse = (pulse_sign) ? pulse - (( leds.mods[5] + 1.0) / 2048.0 ) : pulse + ((leds.mods[5] + 1.0) / 2048.0 ); //slow down pulse rate //avoid divide by 0
				if (pulse > 1) //switch direction of pulse (and max intensity is 1)
					pulse_sign = pulse = 1;
				else if (pulse < ((float) leds.mods[4])/256.0)  //switch direction of pulse if we are at the min pulse intensity.
					pulse_sign = 0;
				if (pulse < 0) //make sure we don't get in a bad state (not mixed with above since min pulse is not always 0).
					pulse = 0;
				
				for ( j = 0; j < 3; j++) {
					for ( t = 0; t < 3; t++ ) {
						leds.rgb[j][t] = leds_orig.rgb[j][t] * pulse;
					}
				}
			}
			
			/****** Build Unit Block *****/
			num_colors = (leds.mode & MODE_THIRDCOLOR) ? 3 : 2;  //this makes sure the wrapping gradient step is computed correctly
			//printf("building %d color gradient with color_len %d, grad_len %d, and offset %d.\n", num_colors, color_len, grad_len, offset);
			p = 0;

			
			//initially we only ran this if grad_len > 0, but the computation is trivial... just set it to 0 if it's unused.
			//One question is if we should keep the same length regardless of colors, or grow per number of colors based on color length...
			//compute gradient step for each of the colors.
			for (t = 0; t < 3; t++) {
				for ( c = 0; c < num_colors; c++) { // technically if we have 2 colors we can do this just once and reverse it... but this is cleaner, and the computation is trivial.
					if ( grad_len > 0 )  //divide by 0 error...
						grad_step[c][t] = ((float)leds.rgb[(c+1)%num_colors][t] - (float)leds.rgb[c][t])/(grad_len);
					else
						grad_step[c][t] = 0;
				}
			}
			
			for (c = 0; c < num_colors; c++) {
				for (j = 0; j <= (color_len - grad_len); j++) { //build solid color.  always have at least one pixel...
					for ( t = 0; t < 3; t++) { //always 3 parts of a color -- rgb
						rgb[p][t] =  leds.rgb[c][t];
					}		
					p++; //next pixel
				}		
				for (j = 1; j < grad_len + 1; j++) { //build gradient (can be 0 and not iterate)
					for ( t = 0; t < 3; t++) { //always 3 parts of a color -- rgb
						rgb[p][t] =  leds.rgb[c][t] + grad_step[c][t]*j;
					}		
					p++; //next pixel
				}		
			}
			
			if (offset > p*4) //modulus doesn't work with floats...  eventually the float precision becomes a problem, so let's keep the offset small.  Also, this gives a cool effect when switching from rotate to sway.
				offset -= p*4;
			else if ( offset < -p*4 )
				offset += p*4;  //note -- we add p*4 below to make sure we never go negative!!
			
			/*print("Offset before: %f   ", offset);
			//offset should *never* be negative, otherwise we get weird wrapping issues!!!!  we'll handle it later though...
			if (offset > p*8) //modulus doesn't work with floats...  eventually the float precision becomes a problem, so let's keep the offset small.  Also, this gives a cool effect when switching from rotate to sway.
				offset -= p*4;
			else if ( offset < 0 ) //use less than so swaying is okay
				offset += p*4;
			print("Offset after: %f   \n", offset);*/
			
			gettimeofday(&tv, NULL);
			//printf("%d us since start of last draw.\n", (tv.tv_usec - tv_last.tv_usec));
			draw(frame, rgb, p, offset+p*4);  //write the colors in rgb to the frame.  p is the pixel index, which is now the length of the entire 2 or 3 color block we want to repeat. // add P*4 to offset so it is always positive.
			gettimeofday(&tv_draw, NULL);
			///printf("Draw took %d us.\n", (tv_draw.tv_usec - tv.tv_usec));
			nanosleep((struct timespec[]){{0, 35000000}}, NULL);  //unfortunate hack to fix ledscape_wait not waiting.
			ledscape_wait(scape);
			gettimeofday(&tv_last, NULL);
			//printf("Wait waited %d us.\n", (tv_last.tv_usec - tv_draw.tv_usec));
			ledscape_draw(scape, frame_num);
			gettimeofday(&tv_draw, NULL);
			//printf("LEDscape draw took %d us.\n\n", (tv_draw.tv_usec - tv_last.tv_usec));
			
			tv_last = tv;
		}

	}
    close(sock);
	ledscape_close(scape);

	return EXIT_SUCCESS;
}
