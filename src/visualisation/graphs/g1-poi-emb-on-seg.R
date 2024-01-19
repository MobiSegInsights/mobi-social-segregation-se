# Title     : Range plots of projections on segregation axis of POIs
# Objective : POI category (x) - Projection on segregation (y)
# Created by: Yuan Liao
# Created on: 2024-01-10

library(dplyr)
library(plyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(magick)
library(ggsci)
options(scipen=10000)

df.poi <- as.data.frame(read_parquet('dbs/graphs/poi_emb_proj_on_seg.parquet'))
df.poi$poi_type <- factor(df.poi$poi_type,
                          levels = c("Education", "Food, Drink, and Groceries", "Mobility",
                                     "Retail", "Recreation", "Health and Wellness", "Other"))
deso_2 <- c("01", "14", "13" , "03", "04" , "05", "06", "07", "08", "09", "10", "12",
            "17", "18", "19", "20", "21", "22", "23", "24", "25")

p<-ggplot(df.poi, aes(x=seg_sim, y=ice_birth, color=poi_type)) +
  geom_point(alpha=0.3) +
  scale_color_npg() +
  theme_classic()
p


p<-ggplot(df.poi[df.poi$ice_birth_cat != 'N', ], aes(x=ice_birth, color=poi_type)) +
  geom_density() +
  scale_color_locuszoom() +
  theme_classic()
p


p<-ggplot(df.poi, aes(x=seg_sim, color=poi_type), alpha=0.4) +
  geom_freqpoly(aes(y=..density..), binwidth = 0.05) +
  scale_color_locuszoom() +
  theme_classic()
p


# ------------------ Density across pois regarding segregation and projection ----
p1 <-ggplot(df.poi,
          aes(x=ice_birth, after_stat(count), fill=poi_type), alpha=0.4) +
  geom_density(position = 'fill') +
  facet_grid(.~region_cat) +
  scale_fill_locuszoom() +
  theme_classic()

p2 <-ggplot(df.poi,
          aes(x=seg_sim, after_stat(count), fill=poi_type), alpha=0.4) +
  geom_density(position = 'fill') +
  facet_grid(.~region_cat) +
  scale_fill_locuszoom() +
  theme_classic()
p <- ggarrange(p1, p2, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="right",
               font.label = list(face = "bold"))
p