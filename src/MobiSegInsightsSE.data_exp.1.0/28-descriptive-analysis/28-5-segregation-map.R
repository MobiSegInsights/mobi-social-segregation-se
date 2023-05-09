# Title     : Experienced/Visiting vs. residential income segregation
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

#------------ Residential vs. visiting --------------
df.deso <- as.data.frame(read_parquet('results/seg_resi_visi.parquet'))
zones <- read_sf('dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'geometry')]
zones.seg <- merge(zones, df.deso, on='deso')
# 01-Stockholm, 14-Gothenburg, 12-Malmö
zones.seg <- zones.seg %>%
  mutate(deso_2 = substr(deso, start = 1, stop = 2))

# Prepare basemaps
# Stockholm
stockholm <- zones.seg[zones.seg$deso_2 == '01',]
stockholm <- st_transform(stockholm, 4326)
bbox <- st_bbox(stockholm)
names(bbox) <- c("left", "bottom", "right", "top")
stockholm_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

# Gothenburg
gothenburg <- zones.seg[zones.seg$deso_2 == '14',]
gothenburg <- st_transform(gothenburg, 4326)
bbox <- st_bbox(gothenburg)
names(bbox) <- c("left", "bottom", "right", "top")
gothenburg_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

# Malmö
malmo <- zones.seg[zones.seg$deso_2 == '12',]
malmo <- st_transform(malmo, 4326)
bbox <- st_bbox(malmo)
names(bbox) <- c("left", "bottom", "right", "top")
malmo_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

# --- Residential on the map ---
my_breaks <-seq(0, 0.8, 0.2)
g1 <- ggplot(zones.seg) +
  geom_sf(aes(fill=Residential), color = NA, alpha=1, show.legend = T) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  coord_sf(datum=st_crs(3006)) +
  theme(legend.position = 'bottom') +
  annotation_scale() +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g2 <- ggmap(stockholm_basemap) +
  geom_sf(data = stockholm, aes(fill=Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g3 <- ggmap(gothenburg_basemap) +
  geom_sf(data = gothenburg, aes(fill=Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g4 <- ggmap(malmo_basemap) +
  geom_sf(data = malmo, aes(fill=Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

# --- Visiting on the map ---
g21 <- ggplot(zones.seg) +
  geom_sf(aes(fill=Visiting), color = NA, alpha=1, show.legend = T) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  coord_sf(datum=st_crs(3006)) +
  theme(legend.position = 'bottom') +
  annotation_scale() +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g22 <- ggmap(stockholm_basemap) +
  geom_sf(data = stockholm, aes(fill=Visiting),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g23 <- ggmap(gothenburg_basemap) +
  geom_sf(data = gothenburg, aes(fill=Visiting),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g24 <- ggmap(malmo_basemap) +
  geom_sf(data = malmo, aes(fill=Visiting),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient(low = "darkblue", high = "yellow",
                      name='Income segregation',
                      breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

G1 <- ggarrange(g1, g21, ncol = 2, nrow = 1, labels = c('(a)', '(b)'), common.legend = T, legend="bottom")
ggsave(filename = "figures/seg_desc_map_se.png", plot=G1,
       width = 10, height = 12, unit = "in", dpi = 300)

G <- ggarrange(g2, g3, g4, g22, g23, g24, ncol = 3, nrow = 2,
               labels = c('(a)', '(b)', '(c)', '(d)', '(e)', '(f)'), common.legend = T, legend="bottom")
ggsave(filename = "figures/seg_desc_map_thr.png", plot=G,
       width = 12, height = 8, unit = "in", dpi = 300)

#---------- Disparity between visiting and residential ----
my_breaks <- seq(-0.4, 0.4, 0.2)
fake_scico <- scico(3, palette = "vik")
g32 <- ggmap(stockholm_basemap) +
  geom_sf(data = stockholm, aes(fill=Visiting-Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name='Disparity in segregation measures',
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g33 <- ggmap(gothenburg_basemap) +
  geom_sf(data = gothenburg, aes(fill=Visiting-Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name='Disparity in segregation measures',
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g34 <- ggmap(malmo_basemap) +
  geom_sf(data = malmo, aes(fill=Visiting-Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name='Disparity in segregation measures',
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

G2 <- ggarrange(g32, g33, g34, ncol = 3, nrow = 1,
               labels = c('(a)', '(b)', '(c)'), common.legend = T, legend="top")
ggsave(filename = "figures/seg_dis_desc_map_thr.png", plot=G2,
       width = 12, height = 4, unit = "in", dpi = 300)

#---------- Hotspot of segregation in Gothenburg area ----

got.hotspot.plot <- function(seg_measure, fill_name){
  # Create the list of neighbors
  gothenburg.ht <- gothenburg
  neighbors <- poly2nb(gothenburg.ht)
  weighted_neighbors <- nb2listw(neighbors, zero.policy=T)

  # Perform the local G analysis (Getis-Ord GI*)
  gothenburg.ht$HOTSPOT <- as.vector(localG(gothenburg.ht[[seg_measure]], weighted_neighbors))
  gothenburg.ht <- gothenburg.ht[!is.na(gothenburg.ht$HOTSPOT),]

  # Keep the significant hotspots
  gothenburg.ht <- gothenburg.ht %>%
    mutate(HOTSPOT_n = ifelse(HOTSPOT > 1.65, HOTSPOT, 0)) %>%
    filter(HOTSPOT_n != 0)

  # New basemap smaller Gothenburg
  bbox <- st_bbox(gothenburg.ht)
  names(bbox) <- c("left", "bottom", "right", "top")
  gothenburg.ht_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

  g43 <- ggmap(gothenburg.ht_basemap) +
    geom_sf(data = gothenburg.ht, aes(fill=.data[[seg_measure]]),
            color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
    scale_fill_gradient(low = "darkblue", high = "yellow",
                        name=fill_name,
                        breaks = seq(0, 6, 0.5), labels = seq(0, 6, 0.5)) +
    theme_void() +
    theme(plot.margin = margin(1,1,0,0, "cm"))
  return(g43)
}
g43 <- got.hotspot.plot('Residential', 'Income segregation')
g53 <- got.hotspot.plot('Visiting', 'Income segregation')

G3 <- ggarrange(g43, g53, ncol = 2, nrow = 1,
               labels = c('(a)', '(b)'), common.legend = T, legend="top")
ggsave(filename = "figures/seg_got.png", plot=G3,
       width = 8, height = 4, unit = "in", dpi = 300)