# Title     : Experienced vs. residential nativity segregation
# Objective : On the map of central Gothenburg
# Created by: Yuan Liao
# Created on: 2023-9-22

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(ggmap)
library(ggspatial)
library(sf)
library(sp)
library(scico)
library(spdep)
library(ggraph)
library(arrow)
library(scales)
library(ggExtra)
library(networkD3)
library(magick)
options(scipen=10000)
ggmap::register_stadiamaps(key='1ffbd641-ab9c-448b-8f83-95630d3c7ee3')

#------------ Experienced vs. residential --------------
fake_scico <- scico(7, palette = "vik")
df.deso <- as.data.frame(read_parquet('results/seg_disparity_map.parquet'))
df.deso$ice_r_g <- cut(df.deso$ice_r, breaks = c(-1, -0.6, -0.4, -0.2, 0.2, 0.4, 0.6, 1))
df.deso$ice_e_g <- cut(df.deso$ice_e, breaks = c(-1, -0.6, -0.4, -0.2, 0.2, 0.4, 0.6, 1))

zones <- read_sf('dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'geometry')]
zones.seg <- merge(zones, df.deso, on='deso', how='inner')
zones.seg <- st_transform(zones.seg, 4326)

# Stockholm
bbox <- c(17.6799476147,59.1174841345,18.4572303295,59.475092515)
names(bbox) <- c("left", "bottom", "right", "top")
stockholm_basemap <- get_stadiamap(bbox, maptype="stamen_toner_lite", zoom = 12)

# Gothenburg
bbox <- c(11.81288,57.623515,12.163069,57.795916)
names(bbox) <- c("left", "bottom", "right", "top")
gothenburg_basemap <- get_stadiamap(bbox, maptype="stamen_toner_lite", zoom = 12)

# Malmö
bbox <- c(12.8617560863,55.4132430111,13.4282386303,55.7174059585)
names(bbox) <- c("left", "bottom", "right", "top")
malmo_basemap <- get_stadiamap(bbox, maptype="stamen_toner_lite", zoom = 12)

# --- Residential on the map ---
g1 <- ggmap(stockholm_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_r_g),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  labs(title = 'Stockholm') +
  scale_fill_scico_d(palette = 'vik', direction = -1, name='') +
  theme_void() +
  theme(plot.margin = margin(0.1,0.1,0.1,0, "cm"),
        legend.position = 'top',
        plot.title = element_text(hjust = 0.5)) +
  guides(fill = guide_legend(nrow = 1))

g2 <- ggmap(gothenburg_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_r_g),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  labs(title = 'Gothenburg') +
  scale_fill_scico_d(palette = 'vik', direction = -1, name='') +
  theme_void() +
  theme(plot.margin = margin(0.1,0.1,0.1,0, "cm"),
        legend.position = 'right',
        plot.title = element_text(hjust = 0.5),
        legend.text=element_text(size=12),
        legend.key.size = unit(1, 'cm')) +
  guides(fill = guide_legend(ncol = 1))

g3 <- ggmap(malmo_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_r_g),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  labs(title = 'Malmo') +
  scale_fill_scico_d(palette = 'vik', direction = -1, name='') +
  theme_void() +
  theme(plot.margin = margin(0.1,0.1,0.1,0, "cm"),
        legend.position = 'top',
        plot.title = element_text(hjust = 0.5)) +
  guides(fill = guide_legend(nrow = 1))

g4 <- ggmap(stockholm_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_e_g),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  scale_fill_scico_d(palette = 'vik', direction = -1, name='') +
  theme_void() +
  theme(plot.margin = margin(0.1,0.1,0.1,0, "cm"),
        legend.position = 'top',
        plot.title = element_text(hjust = 1)) +
  guides(fill = guide_legend(nrow = 1))

g5 <- ggmap(gothenburg_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_e_g),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  scale_fill_scico_d(palette = 'vik', direction = -1, name='') +
  theme_void() +
  theme(plot.margin = margin(0.1,0.1,0.1,0, "cm"),
        legend.position = 'top',
        plot.title = element_text(hjust = 1)) +
  guides(fill = guide_legend(nrow = 1))

g6 <- ggmap(malmo_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_e_g),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  scale_fill_scico_d(palette = 'vik', direction = -1, name='') +
  theme_void() +
  theme(plot.margin = margin(0.1,0.1,0.1,0, "cm"),
        legend.position = 'top',
        plot.title = element_text(hjust = 1)) +
  guides(fill = guide_legend(nrow = 1))

G1 <- ggarrange(g1, g2, g3, ncol = 3, nrow = 1, legend="none")
G1 <- annotate_figure(G1, left = text_grob('Residential', color = "black", size = 12, rot = 90, face='bold'))

G2 <- ggarrange(g4, g5, g6, ncol = 3, nrow = 1, legend="none")
G2 <- annotate_figure(G2, left = text_grob('Experienced', color = "black", size = 12, rot = 90, face='bold'))

G <- ggarrange(G1, G2, ncol = 1, nrow = 2, legend = 'none')
G <- ggarrange(G, get_legend(g2), ncol = 2, nrow = 1, widths = c(1, 0.12))

G <- annotate_figure(G,
                     right = text_grob("-1 <---------- 0 ----------> 1\nForeign-born segregated           Native-born segregated",
                                        color = "black", size = 12, rot = 270)
)


ggsave(filename = "figures/panels/seg_disp_map.png", plot=G,
       width = 12, height = 7, unit = "in", dpi = 300, bg = 'white')

# ------------ Group change figure ------
df.g <- read.csv('results/group_change.csv')
df.g$Residential <- factor(df.g$Residential, levels=c('F', 'N', 'D'),
                              labels=c('Foreign-born', 'Mixed', 'Native-born'))
df.g$Experienced <- factor(df.g$Experienced, levels=c('F', 'N', 'D'),
                              labels=c('Foreign-born', 'Mixed', 'Native-born'))

g7 <- ggplot(df.g, aes(x = Residential, y = Share,
                       fill = Experienced, pattern = Residential)) +
  geom_bar(stat = 'identity') +
  theme_classic() +
  scale_fill_scico_d(palette = 'vik', direction = -1, name='Experienced') +
  geom_text(aes(label = round(Share, digits=2)), colour = "#808e9b", size = 3,
            position = position_stack(vjust = .5), fontface = "bold") +
  theme(legend.position = 'right',
        plot.title = element_text(hjust = 0, face = "bold"),
        text = element_text(size=14),
        axis.text.x = element_text(angle = 30, vjust = 0.5, hjust=0.5))
ggsave(filename = "figures/panels/seg_disp_grp_change.png", plot=g7,
       width = 4, height = 4, unit = "in", dpi = 300)

# ----- Combine labeled images -------
# Load the two input .png images
read.img <- function(path, lb){
  image <- image_read(path) %>%
    image_annotate(lb, gravity = "northwest", color = "black", size = 70, weight = 700)
  return(image)
}
image1 <- read.img(path="figures/panels/seg_disp_map.png", lb='a')
image2 <- read.img(path="figures/panels/seg_disp_res.png", lb='b')
image3 <- read.img(path="figures/panels/seg_disp_FD.png", lb='c')
image4 <- read.img(path="figures/panels/seg_disp_grp_change.png", lb='d')


## Combine images 2-4
# Get width of image 2
image2_height <- image_info(image2)$height

# Create blank space between them and stack three
blank_space_h <- image_blank(2, image2_height, color = "white")
combined_image1 <- image_append(c(image2, blank_space_h, image3,
                                  blank_space_h, image4), stack = F)

## Combine image1 with combined_image1
# Get height of image 1
image1_width <- image_info(image1)$width

# Create a blank space image
blank_space_w <- image_blank(image1_width, 2, color = "white")

# Combine the images side by side
combined_image <- image_append(c(image1, blank_space_w, combined_image1), stack = T)
image_write(combined_image, "figures/panels/seg_disp_fig1.png")