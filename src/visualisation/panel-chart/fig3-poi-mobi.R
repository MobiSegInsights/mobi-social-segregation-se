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
# ----- POI insights ---
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
  labs(y = 'Nativity segregation experienced at POIs',
       x = 'Average distance from residential area (km)') +
  scale_x_continuous(trans='log2') +
  scale_color_npg(name = "POI type") +
  scale_shape_discrete(name = 'Nativity group') +
  guides(size=guide_legend(title="Number of places"),
         color = guide_legend(ncol = 1)) +
  theme(legend.position = c(.05, .85),
        legend.justification = c("left", "top"),
        legend.background = element_blank(),
        legend.box.just = "left",
        legend.margin = margin(6, 6, 6, 6),
        strip.background = element_blank())
g1

# ---- Mobility range ----
df.mobi <- as.data.frame(read_parquet('results/plot/sim2_mobi_range.parquet')) %>%
  filter(grp_r != 'N')
df.mobi$cate_level_numeric <- as.numeric(as.character(df.mobi$cate_level))

df.mobi <- df.mobi %>%
  mutate(grp_r = recode(grp_r, !!!rename_dict))

g21 <- ggplot(data = df.mobi) +
  theme_hc() +
  geom_segment(aes(y = 0, x = 0, yend = 0, xend = 0.25),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(y = 30, x = 0.20), label = "Native-born\n segregated", fill = "white",
               colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_segment(aes(y = 0, x = 0, yend = 0, xend = -0.5),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(y = 30, x = -0.45), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_vline(aes(xintercept = 0), color='gray', linewidth=1) +
  geom_point(aes(y=0, x=0), color='black', size=2) +
  geom_ribbon(aes(y = cate_level_numeric, xmax = q75, xmin = q25, fill = grp_r), color=NA, alpha = 0.3) +
  geom_point(aes(y=cate_level_numeric, x=q50, color = grp_r),
  #           position = position_dodge2(width = 0.8),
             shape = 21, size = 2, fill = "white") +
  labs(x = 'Experienced nativity segregation\noutside residential area',
       y = 'Mobility range (km)') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  scale_fill_manual(name = "Residential nativity group",
                    values = cols) +
  xlim(-0.5, 0.25) +
  coord_flip() +
  theme(legend.position="top", strip.background = element_blank())
g21

# ---- Transport access ----
df.access.0 <- as.data.frame(read_parquet('results/plot/sim2_access.parquet'))

df.access <- as.data.frame(read_parquet('results/plot/sim2_access_car_low.parquet'))
# %>% filter(grp_r == 'F')

g220 <- ggplot(data = na.omit(df.access.0[df.access.0$grp_r == 'F',]),
               aes(x=access_pt, y=q50)) +
  theme_hc() +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=0.6) +
  geom_linerange(aes(ymin=q25, ymax=q75), linewidth=0.3) +
  geom_point(shape = 21, fill = "white", size = 2) +
  geom_smooth(se = FALSE, method = "loess", formula = y ~ x, alpha=0.7) +
  labs(y = 'Experienced nativity segregation\noutside residential area',
       x = 'No. of jobs accessible by transit in 30 min') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  scale_x_continuous(trans = 'log10') +
  ylim(-0.5, 0) +
  facet_grid(car_cat~mobi_range_cat) +
  theme(legend.position="bottom", strip.background = element_blank())
g220

g221 <- ggplot(data = df.access, aes(x=access_pt, y=q50)) +
  theme_hc() +
  geom_segment(aes(x = 300, y = -0.1, xend = 300, yend = -0.5),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 500, y = -0.47), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=0.6) +
  geom_linerange(aes(ymin=q25, ymax=q75), linewidth=0.3, color="#601200") +
  geom_point(shape = 21, fill = "white", size = 2, color="#601200") +
  geom_smooth(se = FALSE, method = "loess", formula = y ~ x, color="#601200", alpha=0.7) +
  labs(y = '',
       x = 'No. of jobs accessible by transit in 30 min') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  scale_x_continuous(trans = 'log10') +
  # ylim(-0.5, -0.1) +
  facet_grid(grp_r~car_cat) +
  theme(legend.position="bottom", strip.background = element_blank())

g221

g22 <- ggplot(data = df.access[(df.access$grp_r == 'F') & (df.access$car_cat == 'L'), ],
              aes(x=access_pt, y=q50)) +
  theme_hc() +
  geom_segment(aes(x = 300, y = -0.1, xend = 300, yend = -0.5),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(aes(x = 500, y = -0.47), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=0.6) +
  # geom_point(aes(x=300, y=0), color='black', size=2) +
  geom_linerange(aes(ymin=q25, ymax=q75), linewidth=0.3, color="#601200") +
  geom_point(shape = 21, fill = "white", size = 2, color="#601200") +
  geom_smooth(se = FALSE, method = "loess", formula = y ~ x, color="#601200", alpha=0.7) +
  labs(y = '',
       x = 'No. of jobs accessible by transit in 30 min') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  scale_x_continuous(trans = 'log10') +
  ylim(-0.5, -0.1) +
  theme(legend.position="bottom", strip.background = element_blank())

g22

# ---- Seg group vs. mobility range ----
df.seg <- as.data.frame(read_parquet('results/plot/seg_grp_vs_rg.parquet')) %>%
  filter(grp_r != 'N') %>%
  mutate(lower = q50-q50_se) %>%
  mutate(upper = q50+q50_se)
var <- 'radius_of_gyration'
df.seg <- df.seg %>%
  mutate(grp_r = recode(grp_r, !!!rename_dict))
cols <- c('N'='#001260', 'F'='#601200', 'M'='gray75')
g31 <- ggplot(data = df.seg, aes(y=seg_cat, color=grp_r)) +
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
  geom_point(aes(x=q50), shape = 21, fill = "white", size = 2) +
  labs(x = 'Mobility range (km)',
       y = 'Experienced nativity segregation outside residential area') +
  scale_color_manual(name = "Residential nativity group",
                     values = cols) +
  scale_fill_manual(name = "Residential nativity group",
                   values = cols) +
  scale_x_continuous(trans = 'log10') +
  ylim(-0.6, 0.4) +
  theme(legend.position="bottom", strip.background = element_blank())
g31

# ---- Seg group vs. transit access ----
var <- 'cum_jobs_pt'
df.seg.acc <- as.data.frame(read_parquet('results/plot/seg_car_grp_vs_pt_access.parquet')) %>%
  filter(grp_r != 'N') %>%
  filter(car_cat == 'L') %>%
  mutate(lower = q50-q50_se) %>%
  mutate(upper = q50+q50_se)

rename_grp_dict <- c(
  D = "Group N",
  F = "Group F"
)
df.seg.acc <- df.seg.acc %>%
  mutate(grp_r = recode(grp_r, !!!rename_grp_dict))
cols <- c('Group N'='#001260', 'Group F'='#601200')

g32 <- ggplot(data = df.seg.acc,
              aes(y=seg_car_cat, x=q50, color=grp_r)) +
  theme_hc() +
  geom_segment(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
               aes(x = 10000, y = 0, xend = 10000, yend = 0.2),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
             aes(x = 11000, y = 0.15), label = "Native-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_segment(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
               aes(x = 10000, y = 0, xend = 10000, yend = -0.6),
               arrow = arrow(type = "closed", length = unit(0.1, "inches")),
               colour = "black", size=0.3) +
  geom_label(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
             aes(x = 11000, y = -0.55), label = "Foreign-born\n segregated", fill = "white",
             colour = "black", size = 3, fontface = "bold", label.size = NA) +
  geom_hline(aes(yintercept = 0), color='gray', linewidth=1) +
  geom_point(data = df.seg.acc[df.seg.acc$grp_r == 'Group F',],
             aes(x=10000, y=0), color='black', size=2) +
  geom_errorbarh(aes(xmin=lower, xmax=upper), height = .02, size=1, alpha=0.3, show.legend = F) +
  geom_point(data = df.seg.acc, shape = 21, fill = "white", size = 2, show.legend = FALSE) +
  labs(x = 'No. of jobs accessible by transit in 30 min',
       y = 'Experienced nativity segregation\n outside residential area') +
  scale_color_manual(name = "Residential \n nativity group",
                     values = cols) +
  scale_x_continuous(trans = 'log10') +
  facet_wrap(~grp_r, scales = "free_x") +
  ylim(-0.6, 0.2) +
  theme(legend.position="right", strip.background = element_blank())
g32

G1 <- ggarrange(g1, g31, ncol = 2, nrow = 1, labels = c('a', 'b'), widths = c(1.2, 1))
G <- ggarrange(G1, g32, ncol = 1, nrow = 2, labels = c('', 'c'), heights = c(1.8, 1))
ggsave(filename = "figures/panels/seg_fig_3.png", plot=G,
       width = 11, height = 12, unit = "in", dpi = 300, bg = 'white')