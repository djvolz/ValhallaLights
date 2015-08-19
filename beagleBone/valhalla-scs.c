/** 
 * Valhalla Single Color Server (SCS).
 * Take a 3 byte UDP packet on the LED_PORT and write it to all of the strips.
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
	const int num_pixels = LEDSCAPE_NUM_LEDS;//1010;
	ledscape_t * const leds = ledscape_init(num_pixels);


	while (1) {
		//clear out the receive buffer, since it contains outdated frames
		while (num_bytes > 0) {
			num_bytes = recv(sock, message, BUF_SIZE, MSG_DONTWAIT);
			if (num_bytes > 2) {
				r = message[0];
				g = message[1];
				b = message[2];
				newdata = 1;
			}
		}
		if (newdata) {
			newdata = 0;
		//if ((num_bytes = read(sock, message, BUF_SIZE)) > 2) {
		//	printf("received: %i %i %i\n", message[0], message[1], message[2]);

			// Alternate frame buffers on each draw command
			const unsigned frame_num = i++ % 2;

			ledscape_frame_t * const frame = ledscape_frame(leds, frame_num); //get frame

			for (unsigned i = 0 ; i < num_pixels ; i++) {
					for (unsigned strip = 0 ; strip < LEDSCAPE_NUM_STRIPS ; strip++) {
							ledscape_set_color(frame, strip, i, message[0], message[1], message[2]);
					}
			}

			const uint32_t response = ledscape_wait(leds);
			ledscape_draw(leds, frame_num);		

		}
		else
			printf("Waiting for ethernet...\n");  //while the socket read is blocking, it does eventually timeout

	}
    close(sock);
//	ledscape_close(leds); //clay: for some reason this segfaults...

	return EXIT_SUCCESS;
}
