# Title     : Range plots of poi and segregation by poi share groups
# Objective : Disparity vs. poi share groups, POI distributions by group
# Created by: Yuan Liao
# Created on: 2024-01-31

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggthemes)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(magick)
options(scipen=10000)

# ----- POI insights ---
df <- as.data.frame(read_parquet('results/seg_range_by_poi_type.parquet')) %>%
  select(poi_type, grp_r, q25, q50, q75) %>%
  mutate(Source = 'Empirical')
df.s1 <- as.data.frame(read_parquet('results/seg_range_by_poi_type_s1.parquet'))
df.s1 <- df.s1 %>%
  group_by(poi_type, grp_r) %>%
  summarise(q25 = mean(q25, na.rm = T),
             q50 = mean(q50, na.rm = T),
            q75 = mean(q75, na.rm = T)) %>%
  mutate(Source = 'Homophily removed')
df.s2 <- as.data.frame(read_parquet('results/seg_range_by_poi_type_s2.parquet'))
df.s2 <- df.s2 %>%
  group_by(poi_type, grp_r) %>%
  summarise(q25 = mean(q25, na.rm = T),
             q50 = mean(q50, na.rm = T),
            q75 = mean(q75, na.rm = T)) %>%
  mutate(Source = 'Limited-travel removed')

df$poi_type <- factor(df$poi_type, levels=c('Retail', 'Financial', 'Office', 'Mobility',
                                            'Health and Wellness', 'Food, Drink, and Groceries',
                                            'Recreation', 'Education', 'Religious'))
df.s1$poi_type <- factor(df.s1$poi_type, levels=c('Retail', 'Financial', 'Office', 'Mobility',
                                            'Health and Wellness', 'Food, Drink, and Groceries',
                                            'Recreation', 'Education', 'Religious'))
df.s2$poi_type <- factor(df.s2$poi_type, levels=c('Retail', 'Financial', 'Office', 'Mobility',
                                            'Health and Wellness', 'Food, Drink, and Groceries',
                                            'Recreation', 'Education', 'Religious'))
df.c <- rbind(df, rbind(df.s1, df.s2))
df.c <- df.c %>%
  filter(grp_r != 'N')
cols <- c('D'='#001260', 'F'='#601200', 'N'='gray75')

g1 <- ggplot(data = df.c) +
  theme_hc() +
  annotate("rect", xmin = -1, xmax = 0, ymin = 0, ymax = 10,
          fill = "#601200", alpha = .1) +
  annotate("rect", xmin = 0, xmax = 1, ymin = 0, ymax = 10,
          fill = "#001260", alpha = .1) +
  geom_vline(aes(xintercept = 0), color='gray', linewidth=0.3) +
  scale_y_discrete() +
  xlim(-1, 1) +
  geom_linerange(aes(y=poi_type, xmin=q25, xmax=q75, color=grp_r),
                 position = position_dodge2(width = 0.8),
                 linewidth=0.5) +
  geom_point(aes(y=poi_type, x=q50, color=grp_r),
             position = position_dodge2(width = 0.8),
             shape = 21, fill = "white", size = 2) +
  labs(y = 'POI type', x = 'Nativity segregation') +
  facet_grid(.~Source) +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  theme(legend.position="bottom", strip.background = element_blank())
g1
# ------ Transport access -----
df.access <- as.data.frame(read_parquet('results/plot/sim2_access.parquet')) %>%
  filter(grp_r != 'N')
cols <- c('D'='#001260', 'F'='#601200', 'N'='gray75')

# Car ownership
df.access.car <- df.access[df.access$cate_name == 'car_cat',]
df.access.car$cate_level <- factor(df.access.car$cate_level, levels = c("L", "M", "H"))

g21 <- ggplot(data = df.access.car) +
  theme_hc() +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=0.3) +
  geom_linerange(aes(x=cate_level, ymin=-q25, ymax=-q75, color=grp_r),
                position = position_dodge2(width = 0.8),
                linewidth=0.5) +
  geom_point(aes(x=cate_level, y=-q50, color=grp_r),
             position = position_dodge2(width = 0.8),
             shape = 21, fill = "white", size = 2) +
  labs(y = '',
       x = 'Car ownership level') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  ylim(-0.1, 0.5) +
  coord_flip() +
  theme(legend.position="bottom", strip.background = element_blank())

# Income level
df.access.inc <- df.access[df.access$cate_name == 'low_inc_cat',]
df.access.inc$cate_level <- factor(df.access.inc$cate_level, levels = c("L", "M", "H"))

g22 <- ggplot(data = df.access.inc) +
  theme_hc() +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=0.3) +
  geom_linerange(aes(x=cate_level, ymin=-q25, ymax=-q75, color=grp_r),
                position = position_dodge2(width = 0.8),
                linewidth=0.5) +
  geom_point(aes(x=cate_level, y=-q50, color=grp_r),
             position = position_dodge2(width = 0.8),
             shape = 21, fill = "white", size = 2) +
  labs(y = 'Reduced nativity segregation',
       x = 'Income level') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  ylim(-0.1, 0.5) +
  coord_flip() +
  theme(legend.position="bottom", strip.background = element_blank())

# Mobility level
df.access.rg <- df.access[df.access$cate_name == 'mobi_range_cat',]
df.access.rg$cate_level <- factor(df.access.rg$cate_level,
                                  levels = c("1", "2", "3",
                                             '4', '5', '6',
                                             '7', '8', '9'))

g23 <- ggplot(data = df.access.rg) +
  theme_hc() +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=0.3) +
  geom_linerange(aes(x=cate_level, ymin=-q25, ymax=-q75, color=grp_r),
                position = position_dodge2(width = 0.8),
                linewidth=0.5) +
  geom_point(aes(x=cate_level, y=-q50, color=grp_r),
             position = position_dodge2(width = 0.8),
             shape = 21, fill = "white", size = 2) +
  labs(y = '',
       x = 'Mobility range group') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  ylim(-0.1, 0.5) +
  coord_flip() +
  theme(legend.position="bottom", strip.background = element_blank())

G2 <- ggarrange(g21, g22, g23, ncol = 3, nrow = 1,
               legend = "none",
               font.label = list(face = "bold"))
G <- ggarrange(g1, G2, ncol = 1, nrow = 2, labels = c('a', 'b'),
               common.legend = T, legend="top",
               font.label = list(face = "bold"))
ggsave(filename = "figures/panels/seg_fig_3.png", plot=G,
       width = 12, height = 7, unit = "in", dpi = 300)