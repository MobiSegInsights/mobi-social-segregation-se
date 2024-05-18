# Title     : Range plots of poi and segregation by poi share groups
# Objective : Disparity vs. poi share groups, POI distributions by group
# Created by: Yuan Liao
# Created on: 2024-03-08

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggrepel)
library(ggsci)
library(ggthemes)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(magick)
options(scipen=10000)
cols <- c('N'='#001260', 'F'='#601200', 'M'='gray75')
rename_dict <- c(
  D = "N",
  N = "M"
)
# ----- POI insights ----
df <- as.data.frame(read_parquet('results/seg_range_by_poi_type.parquet')) %>%
  select(poi_type, grp_r, q25, q50, q75)
df.dist <- as.data.frame(read_parquet('results/d2h_range_by_poi_type.parquet')) %>%
  select(poi_type, grp_r, q50, count) %>%
  mutate(q50 = q50/1000) %>%
  rename(Distance = q50)

df$poi_type <- factor(df$poi_type, levels=c('Retail', 'Financial', 'Office', 'Mobility',
                                            'Health and Wellness', 'Food, Drink, and Groceries',
                                            'Recreation', 'Education', 'Religious'))
df <- merge(df, df.dist, by = c('grp_r', 'poi_type'))
df.labels <- df %>%
  group_by(grp_r) %>%
  arrange(desc(abs(q50))) %>%
  mutate(rank = row_number()) %>%
  filter(rank <= 2 | rank > n() - 2) %>%
  arrange(grp_r, rank) %>%
  filter(grp_r != 'N')

df.labels <- df.labels[!((df.labels$grp_r == 'D') & (df.labels$poi_type == 'Retail')), ]
df <- df %>%
  mutate(grp_r = recode(grp_r, !!!rename_dict))
df.labels <- df.labels %>%
  mutate(grp_r = recode(grp_r, !!!rename_dict))

g1 <- ggplot(data = df[df$grp_r != 'M', ], aes(x=Distance, y=q50, color=poi_type, shape=grp_r)) +
  theme_hc() +
  geom_segment(aes(x = 1, y = 0, xend = 1, yend = 0.25),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 1.2, y = 0.20), label = "Native-born\n segregated", fill = "white",
               colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_segment(aes(x = 1, y = 0, xend = 1, yend = -0.5),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 1.2, y = -0.45), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=1) +
  geom_point(aes(x=1, y=0), color='black', size=2) +
  geom_label_repel(data = df.labels, aes(label = poi_type, color = poi_type),
                 parse = F, fontface = 'bold', nudge_x=-0.17, hjust=0, nudge_y=0.07,
                 alpha = 1, size = 3, label.size = NA, show.legend = FALSE) +
  ylim(-0.5, 0.25) +
  geom_point(aes(size = count), show.legend = T) +
  labs(y = 'Segregation experienced at different venues',
       x = 'Average distance from residential area (km)') +
  scale_x_continuous(trans='log2') +
  scale_color_npg(name = "Venue type") +
  scale_shape_discrete(name = 'Group') +
  guides(size=guide_legend(title="Number of places", ncol=1),
         color = guide_legend(ncol = 1),
         shape=guide_legend(ncol = 2)) +
  theme(legend.position = 'right',
        legend.justification = c("left", "top"),
        legend.background = element_blank(),
        legend.box.just = "left",
        legend.margin = margin(6, 6, 6, 6),
        strip.background = element_blank()) +
  coord_flip()

# ---- Seg group vs. mobility range ----
df.seg <- as.data.frame(read_parquet('results/plot/seg_grp_vs_rg.parquet')) %>%
  filter(grp_r != 'N')

var <- 'radius_of_gyration'
df.seg <- df.seg %>%
  mutate(grp_r = recode(grp_r, !!!rename_dict))
cols <- c('N'='#001260', 'F'='#601200', 'M'='gray75')

g2 <- ggplot(data = df.seg, aes(y=seg_cat, color=grp_r)) +
  theme_hc() +
  geom_segment(aes(x = 5, y = 0, xend = 5, yend = 0.4),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 6, y = 0.35), label = "Native-born\n segregated", fill = "white",
               colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_segment(aes(x = 5, y = 0, xend = 5, yend = -0.6),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 6, y = -0.55), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=1) +
  geom_point(aes(x=5, y=0), color='black', size=2) +
  geom_errorbarh(aes(xmin=lower, xmax=upper), height = .02, size=1, alpha=0.3) +
  geom_point(aes(x=q50_est), shape = 21, fill = "white", size = 2) +
  labs(x = 'Mobility range (km)',
       y = 'Experienced segregation\n outside residential area') +
  scale_color_manual(name = "Birth background group",
                     values = cols) +
  scale_fill_manual(name = "Birth background group",
                   values = cols) +
  scale_x_continuous(trans = 'log10') +
  ylim(-0.6, 0.4) +
  theme(legend.position="top", strip.background = element_blank()) +
  coord_flip()
g2
# ---- Seg group vs. transit access ----
var <- 'cum_jobs_pt'
df.seg.acc <- as.data.frame(read_parquet('results/plot/seg_car_grp_vs_pt_access.parquet')) %>%
  filter(grp_r != 'N') %>%
  filter(car_cat == 'L')

rename_grp_dict <- c(
  D = "Group N",
  F = "Group F"
)
df.seg.acc <- df.seg.acc %>%
  mutate(grp_r = recode(grp_r, !!!rename_grp_dict))
cols <- c('Group N'='#001260', 'Group F'='#601200')

g31 <- ggplot(data = df.seg.acc,
              aes(y=seg_car_cat, x=q50_est, color=grp_r)) +
  theme_hc() +
  geom_segment(aes(x = 10000, y = 0, xend = 10000, yend = 0.2),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 13000, y = 0.15), label = "Native-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_segment(aes(x = 10000, y = 0, xend = 10000, yend = -0.6),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 13000, y = -0.55), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=1) +
  geom_point(aes(x=10000, y=0), color='black', size=2) +
  geom_errorbarh(aes(xmin=lower, xmax=upper, color=grp_r),
                 height = .02, size=1, alpha=0.3, show.legend = T) +
  geom_point(data = df.seg.acc, aes(color=grp_r),
             shape = 21, fill = "white", size = 2, show.legend = T) +
  labs(x = 'No. of jobs accessible by transit in 30 min',
       y = 'Experienced segregation\n outside residential area') +
  scale_color_manual(name = "Birth background",
                     values = cols) +
  scale_x_continuous(trans = 'log10') +
  ylim(-0.6, 0.2) +
  theme(legend.position="top", strip.background = element_blank()) +
  coord_flip()

g32 <- ggplot(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
              aes(y=seg_car_cat, x=q50_est, color=grp_r)) +
  theme_hc() +
  geom_segment(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
               aes(x = 14000, y = 0, xend = 14000, yend = 0.2),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
             aes(x = 14500, y = 0.15), label = "Native-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_segment(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
               aes(x = 14000, y = 0, xend = 14000, yend = -0.6),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
             aes(x = 14500, y = -0.55), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=1) +
  geom_point(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
             aes(x=10000, y=0), color='black', size=2) +
  geom_errorbarh(aes(xmin=lower, xmax=upper), height = .02, size=1, alpha=0.3, show.legend = F) +
  geom_point(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
             shape = 21, fill = "white", size = 2, show.legend = FALSE) +
  labs(x = '',
       y = 'Experienced segregation\n outside residential area') +
  scale_color_manual(name = "Residential \n nativity group",
                     values = cols) +
  scale_x_continuous(trans = 'log10') +
  ylim(-0.6, 0.2) +
  xlim(14000, 23000)+
  theme(legend.position="right", strip.background = element_blank()) +
  coord_flip()

G1 <- ggarrange(g1, g2, ncol = 2, nrow = 1, labels = c('a', 'b'), widths = c(1.4, 1))
G2 <- ggarrange(g31, g32, ncol = 2, nrow = 1, labels = c('c', ''), heights = c(1, 1))

G <- ggarrange(G1, G2, ncol = 1, nrow = 2, heights = c(1, 1))
ggsave(filename = "figures/panels/seg_fig_3.png", plot=G,
       width = 12, height = 10, unit = "in", dpi = 300, bg = 'white')