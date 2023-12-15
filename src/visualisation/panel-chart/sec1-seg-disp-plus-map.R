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
fake_scico <- scico(3, palette = "vik")
df.deso <- as.data.frame(read_parquet('../../../results/seg_disparity_map.parquet'))
zones <- read_sf('../../../dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'geometry')]
zones.seg <- merge(zones, df.deso, on='deso', how='inner')
zones.seg <- st_transform(zones.seg, 4326)

# Gothenburg
bbox <- c(11.81288,57.623515,12.163069,57.795916)
names(bbox) <- c("left", "bottom", "right", "top")
gothenburg_basemap <- get_stadiamap(bbox, maptype="stamen_toner_lite", zoom = 12)

# --- Residential on the map ---
my_breaks <-seq(-1, 1, 0.2)

g1 <- ggmap(gothenburg_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_r),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name='ICE',
                       low = fake_scico[3], mid=fake_scico[2], high = fake_scico[1],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(-0.8,0.2,-0.8,0, "cm"),
        legend.key.width = unit(0.2, "cm"),
        legend.key.height = unit(1.2, "cm"))

g2 <- ggmap(gothenburg_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_e),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name='ICE',
                       low = fake_scico[3], mid=fake_scico[2], high = fake_scico[1],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(-0.8,0.2,-0.8,0, "cm"),
        legend.key.width = unit(0.2, "cm"),
        legend.key.height = unit(1.2, "cm"))

G <- ggarrange(g1, g2, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="right",
               font.label = list(face = "bold"))
ggsave(filename = "../../../figures/seg_disp_map.png", plot=G,
       width = 8, height = 4, unit = "in", dpi = 300)


# ----- Combine labeled images -------
# Load the two input .png images
image1 <- image_read("../../../figures/seg_disp_map.png")
image2 <- image_read("../../../figures/seg_disp_res.png")
image3 <- image_read("../../../figures/seg_disp_FD.png")

# Get the dimensions (width and height) of image1
image1_width <- image_info(image1)$width
image2_height <- image_info(image2)$height

# Create a blank space image
blank_space_w <- image_blank(image1_width, 5, color = "white")
blank_space_h <- image_blank(5, image2_height, color = "white")

# Combine the images horizontally (side by side)
combined_image2 <- image_append(c(image2, blank_space_h, image3), stack = FALSE)
combined_image <- image_append(c(image1, blank_space_w, combined_image2), stack = TRUE)
combined_image3 <- image_append(c(image1, blank_space_h, image2, blank_space_h, image3), stack = FALSE)
image_write(combined_image, "../../../figures/seg_disp_fig1.png")