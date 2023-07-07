# Title     : STRC 2023
# Objective : Impact of transport accessibility and income on nativity segregation in Sweden:
# a mobility perspective using big geolocation data
# Created by: Yuan Liao
# Created on: 2023-6-25

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
library(yaml)
library(DBI)
library(tidyr)
options(scipen=10000, digits=2)

#------------ Data location --------------
keys_manager <- read_yaml('../../dbs/keys.yaml')
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

#------------ Residential vs. experienced --------------
fake_scico <- scico(3, palette = "vik")
df.vis <- as.data.frame(read_parquet('../../results/seg_disparity_exp_nativity.parquet'))
df.deso <- df.vis %>%
  group_by(deso) %>%
  summarise(Residential=weighted.mean(Residential, wt_p),
            Experienced=weighted.mean(Experienced, wt_p))

zones <- read_sf('../../dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'geometry')]
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

seg.name <- 'Nativity segregation (ICE)'
# --- Residential on the map ---
my_breaks <-seq(-1, 1, 0.2)

g2 <- ggmap(stockholm_basemap) +
  geom_sf(data = stockholm, aes(fill=Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name=seg.name,
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

g3 <- ggmap(gothenburg_basemap) +
  geom_sf(data = gothenburg, aes(fill=Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name=seg.name,
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

g4 <- ggmap(malmo_basemap) +
  geom_sf(data = malmo, aes(fill=Residential),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name=seg.name,
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

# --- Visiting on the map ---

g22 <- ggmap(stockholm_basemap) +
  geom_sf(data = stockholm, aes(fill=Experienced),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name=seg.name,
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

g23 <- ggmap(gothenburg_basemap) +
  geom_sf(data = gothenburg, aes(fill=Experienced),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name=seg.name,
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

g24 <- ggmap(malmo_basemap) +
  geom_sf(data = malmo, aes(fill=Experienced),
          color = NA, alpha=0.6, show.legend = T, inherit.aes = FALSE) +
  scale_fill_gradient2(name=seg.name,
                       low = fake_scico[1], mid=fake_scico[2], high = fake_scico[3],
                       breaks = my_breaks, labels = my_breaks) +
  theme_void() +
  theme(plot.margin = margin(1,1,0,0, "cm"), legend.key.width = unit(2.5, "cm"))

G1 <- ggarrange(g2, g3, g4, g22, g23, g24, ncol = 3, nrow = 2,
               labels = c('(a)', '(b)', '(c)', '(d)', '(e)', '(f)'),
                common.legend = T, legend="bottom")

#------------ Experienced segregion --------------
fb.tre.low <- 0.4
fb.tre.high <- 0.1
df.vis.imp <- df.vis
df.vis$income_gp <- NA
df.vis$income_gp[df.vis$`Lowest income group` > fb.tre.low] <- "Low income"
df.vis$income_gp[df.vis$`Lowest income group` <= fb.tre.high] <- "High income"
#Remove rows with NA's using rowSums()
df.vis <- df.vis[rowSums(is.na(df.vis)) == 0, ]
df.vis$disparity <- df.vis$Experienced - df.vis$Residential

g5 <- ggplot(data=df.vis, aes(x=Residential, y=disparity, color=income_gp)) +
  scale_color_manual(name='Income group',
                 breaks=c('High income', 'Low income'),
                 values=c('High income'='steelblue', 'Low income'='orange')) +
  geom_hdr_lines(show.legend = T) +
  #geom_point(size=1, alpha=0.7) +
  labs(y = 'Experienced - Residential', x = 'Residential nativity segregation') +
  theme_minimal() +
  theme(legend.position="top", legend.box="vertical")

#----------------Impact of access and income level
qtls <- lapply(seq(0, 100, 10),
               function(x){quantile(df.vis.imp$Experienced, x/100, na.rm=T)})
lbls <- names(unlist(qtls))
df.vis.imp$exp_grp <- cut(df.vis.imp$Experienced, breaks = qtls)

df.vis.imp <- drop_na(df.vis.imp)
# df.vis.inc <- df.vis.imp %>%
#   group_by(Income)  %>%
#   summarise(Experienced = weighted.mean(Experienced),
#             )
g6 <- ggplot(data=df.vis.imp, aes(x=`Lowest income group`, y=exp_grp)) +
  geom_boxplot(width = 0.3, outlier.alpha = 0.1) +
  labs(y = 'Experienced nativity segregation', x = 'Share of lowest income group') +
  theme_minimal() +
  theme(legend.position="top",
        legend.key.width = unit(2.5, "cm"))

g7 <- ggplot(data=df.vis.imp, aes(x=cum_jobs/1000, y=exp_grp)) +
  geom_boxplot(width = 0.3, outlier.alpha = 0.1) +
  labs(y = 'Experienced nativity segregation', x = 'Car accessibility (1k jobs)') +
  theme_minimal() +
  theme(legend.position="top",
        legend.key.width = unit(2.5, "cm"))

g8 <- ggplot(data=df.vis.imp, aes(x=cum_stops, y=exp_grp)) +
  geom_boxplot(width = 0.3, outlier.alpha = 0.1) +
  labs(y = 'Experienced nativity segregation', x = 'Transit accessibility (1 stop), log scale') +
  scale_x_continuous(trans='log10') +
  theme_minimal() +
  theme(legend.position="top",
        legend.key.width = unit(2.5, "cm"))

G2 <- ggarrange(g5, g6, g7, g8, ncol = 2, nrow = 2,
               labels = c('(g)', '(h)', '(i)', '(j)'))

G <- ggarrange(G1, G2, ncol = 2, nrow = 1, widths = c(1, 1))
ggsave(filename = paste0("figures/", 'mobi_seg_strc.png'), plot=G,
       width = 16, height = 7, unit = "in", dpi = 300)