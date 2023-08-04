# Title     : Population representation
# Objective : Value difference on maps
# Created by: Yuan Liao
# Created on: 2022-10-18

library(dplyr)
library(ggplot2)
library(ggsci)
library(ggpubr)
library(ggmap)
library(ggspatial)
library(sf)
library(ggraph)
library(scico)
library(yaml)
library(DBI)
library(scales)

# Load detected home from the database
keys_manager <- read_yaml('dbs/keys.yaml')
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
df <- dbGetQuery(con, 'SELECT * FROM public.home_p')
zones <- read_sf('dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'befolkning', 'geometry')]
df.pop <- df %>%
  group_by(deso) %>%
  count()
zones.pop <- merge(zones, df.pop, on='deso')
zones.pop <- zones.pop %>%
  mutate(pop_share = n/befolkning*100,
         deso_5 = substr(deso, start = 1, stop = 5))

g1 <- ggplot(zones.pop[zones.pop$pop_share < 100,]) +
  geom_point(aes(x=befolkning, y=n), show.legend = F,
             alpha=1, size=0.2, color='steelblue') +
  labs(x='Population size', y='Mobile device count') +
  scale_x_log10() +
  scale_y_log10() +
  geom_abline(intercept = 0, slope = 0.013, size=0.3, color='gray45') +
  theme_minimal() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

my_breaks <- c(0.05, 0.1, 1, 2, 5, 10, 20, 30)
g2 <- ggplot(zones.pop[zones.pop$pop_share < 100,]) +
  geom_sf(aes(fill=pop_share), color = NA, alpha=1, show.legend = T) +
  scale_fill_gradient(low = "darkblue", high = "yellow", trans = "log",
                      name="Device count\n/population (%)",
                      breaks = my_breaks, labels = my_breaks) +
  coord_sf(datum=st_crs(3006)) +
  theme(legend.position = 'bottom') +
#  geom_sf(data = county, color = 'white', alpha=1, fill=NA, size=0.3) +
  annotation_scale(location='tl') +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

abnormal_zones_stockholm <- zones.pop[(zones.pop$pop_share > 100) & (zones.pop$deso_5 == '0180C'),]
abnormal_zones_stockholm <- st_transform(abnormal_zones_stockholm, 4326)
bbox <- st_bbox(abnormal_zones_stockholm)
names(bbox) <- c("left", "bottom", "right", "top")
stockholm_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 16)

g3 <- ggmap(stockholm_basemap) +
  geom_sf(data = abnormal_zones_stockholm,
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE, fill='yellow') +
  # scale_fill_gradient(low = "darkblue", high = "yellow", trans = "log",
  #                     name='Population (%)') +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

abnormal_zones_vg <- zones.pop[(zones.pop$pop_share > 100) &
                                 (zones.pop$deso_5 %in% c('1480C')),]
abnormal_zones_vg <- st_transform(abnormal_zones_vg, 4326)
bbox <- st_bbox(abnormal_zones_vg)
names(bbox) <- c("left", "bottom", "right", "top")
vg_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 16)

g4 <- ggmap(vg_basemap) +
  geom_sf(data = abnormal_zones_vg,
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE, fill='yellow') +
  # scale_fill_gradient(low = "darkblue", high = "yellow", trans = "log",
  #                     name='Population (%)') +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

abnormal_zones_ss <- zones.pop[(zones.pop$pop_share > 100) &
                                 (zones.pop$deso_5 %in% c('1980C')),]
abnormal_zones_ss <- st_transform(abnormal_zones_ss, 4326)
bbox <- st_bbox(abnormal_zones_ss)
names(bbox) <- c("left", "bottom", "right", "top")
ss_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 16)

g5 <- ggmap(ss_basemap) +
  geom_sf(data = abnormal_zones_ss,
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE, fill='yellow') +
  # scale_fill_gradient(low = "darkblue", high = "yellow", trans = "log",
  #                     name='Population (%)') +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

G1 <- ggarrange(g1, g2, ncol = 2, nrow = 1, widths = c(0.6, 0.4), labels = c('(a)', '(b)'))
ggsave(filename = "figures/homes_desc.png", plot=G1,
       width = 7, height = 4, unit = "in", dpi = 300)

G2 <- ggarrange(g3, g5, g4, ncol = 3, nrow = 1, labels = c('(c)', '(d)', '(e)'))
G <- ggarrange(G1, G2, ncol = 1, nrow = 2)
ggsave(filename = "figures/homes_desc_sub.png", plot=G,
       width = 12, height = 8, unit = "in", dpi = 300)