# Title     : Spatial unit visualization
# Objective : On the map
# Created by: Yuan Liao
# Created on: 2023-5-08

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
library(yaml)
library(DBI)
options(scipen=10000)

#------------ Data location --------------
keys_manager <- read_yaml('./dbs/keys.yaml')
user <- keys_manager$database$user
password <- keys_manager$database$password
port <- keys_manager$database$port
db_name <- keys_manager$database$name
con <- DBI::dbConnect(RPostgres::Postgres(),
                      host = "localhost",
                      dbname = db_name,
                      user = user,
                      password = password,
                      port = port)

#------------ DeSO zones vs. Population grids --------------
zones <- read_sf('dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'befolkning', 'geometry')]
# 01-Stockholm, 14-Gothenburg, 12-Malmö
zones <- zones %>%
  mutate(deso_2 = substr(deso, start = 1, stop = 2))
grids <- st_read(con, query = 'SELECT zone, pop, geom FROM grids')

# Prepare basemaps
# Stockholm
stockholm <- zones[zones$deso_2 == '01',]
stockholm <- st_transform(stockholm, 4326)
bbox <- st_bbox(stockholm)
names(bbox) <- c("left", "bottom", "right", "top")
stockholm_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

# Gothenburg
gothenburg <- zones[zones$deso_2 == '14',]
gothenburg <- st_transform(gothenburg, 4326)
bbox <- st_bbox(gothenburg)
names(bbox) <- c("left", "bottom", "right", "top")
gothenburg_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

# Malmö
malmo <- zones[zones$deso_2 == '12',]
malmo <- st_transform(malmo, 4326)
bbox <- st_bbox(malmo)
names(bbox) <- c("left", "bottom", "right", "top")
malmo_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

# ---------- Population distribution ------------
g1 <- ggplot(zones) +
  geom_sf(aes(fill=befolkning/1000), color = NA, alpha=1, show.legend = T) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Population size (K)') +
  coord_sf(datum=st_crs(3006)) +
  theme(legend.position = 'bottom') +
  annotation_scale() +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"),
        legend.position = 'top')

g2 <- ggplot(grids) +
  geom_sf(aes(fill=pop/1000), color = NA, alpha=1, show.legend = T) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Population size (K)', trans = 'log',
                      breaks = c(1/1000, 1/100, 1/10, 1, 5)) +
  coord_sf(datum=st_crs(3006)) +
  annotation_scale() +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"),
        legend.position = 'top')

G <- ggarrange(g1, g2, ncol = 2, nrow = 1, labels = c('(a)', '(b)'))

# ------ Three areas -----
my_breaks <- c(1, 2, 3, 4, 5)
g21 <- ggmap(stockholm_basemap) +
  geom_sf(data = stockholm, aes(fill=befolkning/1000),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Population size (K)',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g22 <- ggmap(gothenburg_basemap) +
  geom_sf(data = gothenburg, aes(fill=befolkning/1000),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Population size (K)',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g23 <- ggmap(malmo_basemap) +
  geom_sf(data = malmo, aes(fill=befolkning/1000),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Population size (K)',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

G1 <- ggarrange(g21, g22, g23, ncol = 1, nrow = 3, labels = c('(c)', '(d)', '(e)'),
                common.legend = T, legend="bottom")
G2 <- ggarrange(G, G1, widths = c(1, 0.8), ncol = 2, nrow = 1)
ggsave(filename = "figures/spatial_units_map.png", plot=G2,
       width = 12, height = 8, unit = "in", dpi = 300)