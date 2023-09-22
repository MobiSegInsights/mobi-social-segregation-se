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
options(scipen=10000)

#------------ Experienced vs. residential --------------
fake_scico <- scico(3, palette = "vik")
df.deso <- as.data.frame(read_parquet('results/seg_disparity_map.parquet'))
zones <- read_sf('dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'geometry')]
zones.seg <- merge(zones, df.deso, on='deso', how='inner')
zones.seg <- st_transform(zones.seg, 4326)

# Gothenburg
bbox <- c(11.694011712,57.5930115688,12.2610291722,57.8377094104)
names(bbox) <- c("left", "bottom", "right", "top")
gothenburg_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 12)

# --- Residential on the map ---
my_breaks <-seq(-1, 1, 0.2)

g1 <- ggmap(gothenburg_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_r),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name='',
                       low = fake_scico[3], mid=fake_scico[2], high = fake_scico[1],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(-0.8,0.2,-0.8,0, "cm"),
        legend.key.width = unit(0.2, "cm"),
        legend.key.height = unit(1.2, "cm"))

g2 <- ggmap(gothenburg_basemap) +
  geom_sf(data = zones.seg, aes(fill=ice_e),
          color = NA, alpha=0.7, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name='',
                       low = fake_scico[3], mid=fake_scico[2], high = fake_scico[1],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(-0.8,0.2,-0.8,0, "cm"),
        legend.key.width = unit(0.2, "cm"),
        legend.key.height = unit(1.2, "cm"))

G <- ggarrange(g1, g2, ncol = 2, nrow = 1,
               labels = c('(b)', '(c)'), common.legend = T, legend="right")
ggsave(filename = "figures/seg_disp_map.png", plot=G,
       width = 8, height = 3.5, unit = "in", dpi = 300)
