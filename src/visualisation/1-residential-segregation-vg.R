# Title     : Share of non-swedish vs. income for VG
# Objective : Deso zones
# Created by: Yuan Liao
# Created on: 2022-09-22

library(dplyr)
library(ggplot2)
library(ggsci)
library(ggspatial)
library(ggsn)
library(ggmap)
library(ggpubr)
library(sf)
library(ggraph)
library(scico)
library(yaml)
library(DBI)
library(scales)

# Load DeSO zones
zones <- read_sf('dbs/DeSO/demo_desos.shp')
zones <- zones[,c('deso', 'geometry')]

df <- read.csv('results/demo.csv')

zones.stats <- right_join(x = zones, y = df, by = c("deso"="deso"), all.y = TRUE)
zones.stats.plot <- st_transform(zones.stats, 4326)
# Get basemap as the background
bbox <- st_bbox(zones.stats.plot)
names(bbox) <- c("left", "bottom", "right", "top")
vgr_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 11)


g1 <- ggmap(vgr_basemap) +
  geom_sf(data = zones.stats.plot, aes(fill = pop_nse*100), color=NA, show.legend = T,
          inherit.aes = FALSE, alpha=0.6) +
  scale_fill_viridis(trans = 'log10') +
  north(zones.stats.plot, location = "topright") +
  annotation_scale() +
  labs(fill='Share of non Swedish population (%)') +
  theme_void() +
  theme(legend.position = 'top', plot.margin = margin(0,1,0,0, "cm"))

g2 <- ggmap(vgr_basemap) +
  geom_sf(data = zones.stats.plot, aes(fill = income), color=NA, show.legend = T,
          inherit.aes = FALSE, alpha=0.6) +
  scale_fill_viridis(trans = 'log10') +
  north(zones.stats.plot, location = "topright") +
  annotation_scale() +
  labs(fill='Net income (median, KSEK)') +
  theme_void() +
  theme(legend.position = 'top', plot.margin = margin(0,1,0,0, "cm"))

G <- ggarrange(g1, g2, ncol = 2, nrow = 1, labels = c('(a)', '(b)'))
ggsave(filename = paste0("figures/demo.png"), plot=G,
       width = 10, height = 5, unit = "in", dpi = 300)
