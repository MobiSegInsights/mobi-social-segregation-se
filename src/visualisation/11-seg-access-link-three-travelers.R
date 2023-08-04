# Title     : Three types of travelers
# Objective : Visualize the clusters and their urban/rural division
# Created by: Yuan Liao
# Created on: 2023-07-31

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
library(weights)
library(scales)
library(ggExtra)
library(tidyr)
options(scipen=10000, digits=2)

#---------------- Travelers' profiles -------------
df.stats <- as.data.frame(read_parquet('results/transport_association/three_travelers.parquet'))
df.stats$ctrl_grp <- factor(df.stats$ctrl_grp, levels = c(1, 0, 2),
                            labels = c("ThriftyMove", "ProsperDrive", "EliteWander"))
# 1. Visualise three traveler profiles
cols.thr <- c('#e25078', '#4587ec', '#11dd66')
plotProf <- function(df, var, ylab){
  g <- ggplot(data = df[df['var'] == var, ]) +
    theme_minimal() +
    geom_linerange(aes(x=ctrl_grp, ymin=q25, ymax=q75, color=ctrl_grp),
                   linewidth=0.5, show.legend = FALSE) +
    geom_point(aes(x=ctrl_grp, y=q50, color=ctrl_grp),
               shape = 21, fill = "white", size = 2, show.legend = FALSE) +
    scale_color_manual(values = cols.thr) +
    theme(axis.text.x = element_text(colour = cols.thr)) +
    labs(x = "Three types of travelers", y = ylab)
  return(g)
}

g1 <- plotProf(df=df.stats, var='Lowest income group', ylab="Share of lowest income")
g2 <- plotProf(df=df.stats, var='car_ownership', ylab="Car ownership")
g3 <- plotProf(df=df.stats, var='radius_of_gyration', ylab="Mobility range (km)")
G1 <- ggarrange(g1, g2, g3, ncol = 1, nrow = 3)

#---------------- Travelers on the map of Sweden -------------
sm <- 500
x <- do.call(c, sapply(1:(sm*sqrt(3)/2)/sm,
                       function(i) (i*sm/sqrt(3)):(sm-i*sm/sqrt(3))/sm))
y <- do.call(c, sapply(1:(sm*sqrt(3)/2)/sm,
                       function(i) rep(i, length((i*sm/sqrt(3)):(sm-i*sm/sqrt(3))))))
d.red <- y
d.green <- abs(sqrt(3) * x - y) / sqrt(3 + 1)
d.blue <- abs(- sqrt(3) * x - y + sqrt(3)) / sqrt(3 + 1)
g0 <- ggplot() +
  theme_void() +
  geom_point(aes(x=x, y=y), color=rgb(d.red, d.green, d.blue), pch=19) +
  geom_text(aes(x=0.5, y = 1), label="ThriftyMove",
            color = "#e25078", show.legend = F) +
  geom_text(aes(x=-0.1, y = -0.1), label="ProsperDrive",
            color = "#4587ec", show.legend = F) +
  geom_text(aes(x=1.1, y = -0.1), label="EliteWander",
            color = "#11dd66", show.legend = F) +
  theme(plot.margin = margin(0,1,0,0, "cm")) +
  xlim(-2, 1.7) +
  ylim(-0.5, 1) +
  coord_fixed()

df.share <- as.data.frame(read_parquet('results/transport_association/three_travelers_distr.parquet'))
# , axis.text.x = element_text(angle = 30, hjust=1)
g01 <- ggplot(df.share, aes(x=region_cat2, y=ctrl_grp)) +
  geom_tile(colour = "gray", fill = "white") +
  geom_text(aes(label = signif(Share, 3), color = Share), show.legend = F) +
  theme_minimal() +
  theme(panel.grid = element_blank(),
        plot.margin = margin(1,0,0,0, "cm")) +
  labs(x='', y='') +
  scale_x_discrete(position = "top") +
  scale_y_discrete(limits=rev)

zones <- read_sf('dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'geometry')]
df.zones <- as.data.frame(read_parquet('results/transport_association/three_travelers_deso.parquet'))
df.zones <- merge(zones, df.zones, on='deso', how='left')
# 01-Stockholm, 14-Gothenburg, 12-Malmö
df.zones <- df.zones %>%
  mutate(deso_2 = substr(deso, start = 1, stop = 2))
# Prepare basemaps
# Stockholm
stockholm <- df.zones[df.zones$deso_2 == '01',]
stockholm <- st_transform(stockholm, 4326)
bbox <- st_bbox(stockholm)
names(bbox) <- c("left", "bottom", "right", "top")
stockholm_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

# Gothenburg
gothenburg <- df.zones[df.zones$deso_2 == '14',]
gothenburg <- st_transform(gothenburg, 4326)
bbox <- st_bbox(gothenburg)
names(bbox) <- c("left", "bottom", "right", "top")
gothenburg_basemap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)

g4 <- ggplot(df.zones) +
  geom_sf(aes(fill=deso), color = NA, alpha=0.6, show.legend = F) +
  scale_fill_manual('Traveler composition', values = df.zones$color) +
  coord_sf(datum=st_crs(3006)) +
  theme(legend.position = 'bottom') +
  annotation_scale(location='tl') +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"))

g5 <- ggmap(stockholm_basemap) +
  geom_sf(data = stockholm, aes(fill=deso),
          color = NA, alpha=0.6, show.legend = F, inherit.aes = FALSE) +
  scale_fill_manual(values = stockholm$color) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

g6 <- ggmap(gothenburg_basemap) +
  geom_sf(data = gothenburg, aes(fill=deso),
          color = NA, alpha=0.6, show.legend = F, inherit.aes = FALSE) +
  scale_fill_manual(values = gothenburg$color) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

G0 <- ggarrange(g01, g0, ncol = 2, nrow = 1, labels = c('(b)', ''))
G2 <- ggarrange(g5, g6, ncol = 1, nrow = 2, labels = c('(d)', '(e)'))
G3 <- ggarrange(g4, G2, ncol = 2, nrow = 1, labels = c('(c)', ''))
G4 <- ggarrange(G0, G3, ncol = 1, nrow = 2, heights=c(0.2, 0.8))
G <- ggarrange(G1, G4, ncol = 2, nrow = 1, widths = c(0.3, 0.7), labels = c('(a)', ''))
ggsave(filename = "figures/three_travelers.png", plot=G,
       width = 12, height = 10, unit = "in", dpi = 300)