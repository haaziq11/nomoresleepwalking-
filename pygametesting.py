import pygame
import sys


pygame.init()
pygame.mixer.init()  


screenwidth = 600
screenheight = 600
window = pygame.display.set_mode((screenwidth, screenheight))
pygame.display.set_caption("DP3 - Team 17")


#loading background and scaling to fit the screen
background = pygame.image.load("sky600.jpg")
background = pygame.transform.scale(background, (screenwidth, screenheight))

# loading power button image
button_on = pygame.image.load("poweron250.png")
# centering the button in the middle of the screen
button_rect = button_on.get_rect(center=(screenwidth // 2, screenheight // 2))

# app states
homepage = "home"
blankpage = "blank"
current_state = homepage

#main
running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            #not running anymore quick boolean
        # Handle mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            if current_state == homepage:
                #click in button?
                if button_rect.collidepoint(event.pos):
                    current_state = blankpage

    #drawing
    if current_state == homepage:

        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load('giveonHA.mp3')
            pygame.mixer.music.play(loops=-1, start=10.0)
            pygame.mixer.music.set_volume(0.25)
        window.blit(background, (0, 0))
        window.blit(button_on, button_rect)
    elif current_state == blankpage:
        #white screen if state changed
        window.fill((255, 255, 255))

    #update display this is the sprite sheet draw flips everything could use update idk
    pygame.display.flip()

#exit conditions
pygame.quit()
sys.exit()
