# Title     : Range plots of poi and segregation by poi share groups
# Objective : Disparity vs. poi share groups, POI distributions by group
# Created by: Yuan Liao
# Created on: 2023-12-14

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(magick)
options(scipen=10000)

df.poi <- as.data.frame(read_parquet('results/poi_share_range_by_group.parquet'))
df.seg <- as.data.frame(read_parquet('results/seg_sims_range_by_group_x_poi.parquet'))
df.poi.grp.seg <- as.data.frame(read_parquet('results/seg_sims_range_by_group_x_poi_grp.parquet'))

df.poi <- df.poi %>%
  filter(grp_r!='N')
df.poi$grp_r <- factor(df.poi$grp_r, levels = c("D", "F"))
df.poi$poi_type <- factor(df.poi$poi_type,
                          levels = c('Education', 'Health and Wellness',
                                     'Food, Drink, and Groceries','Retail',
                                     'Recreation', 'Mobility', 'Other'))

ice.names <- c('Residential', 'Experienced', 'Experienced (outside home)',
               'Homophily simulated (outside home)', 'Limited-travel simulated (outside home)',
               'Homophily effect', 'Limited-travel effect')

df.seg <- df.seg %>%
  filter(grp_r!='N')
df.seg$grp_r <- factor(df.seg$grp_r, levels = c("D", "F"))
df.seg$poi_var_level <- factor(df.seg$poi_var_level,
                          levels = c('Q1', 'Q2', 'Q3', 'Q4'))
df.seg$var <- factor(df.seg$var, levels = c("ice_r", "ice_e", "ice_enh", "ice_e1", "ice_e2",
                                            'delta_ice1', 'delta_ice2'),
                 labels = ice.names)

df.poi.grp.seg <- df.poi.grp.seg %>%
  filter(grp_r!='N')
df.poi.grp.seg$grp_r <- factor(df.poi.grp.seg$grp_r, levels = c("D", "F"))
df.poi.grp.seg$poi_grp_name <- factor(df.poi.grp.seg$poi_grp_name,
                          levels = c('Students' , 'Regular travelers', 'Recreation enthusiasts', 'Foodies',
                                     'Wellness seekers', 'Navigators', 'Shoppers'))
df.poi.grp.seg$var <- factor(df.poi.grp.seg$var, levels = c("ice_r", "ice_e", "ice_enh", "ice_e1", "ice_e2",
                                                            'delta_ice1', 'delta_ice2'),
                             labels = ice.names)
# --- POI share values by POI type x D/F group
plot.poi <- function(data, y.lab='Fraction of recorded time outside home', y.lm=c(0, 1)){
  g <- ggplot() +
    theme_classic() +
    geom_linerange(data = data, aes(x=poi_type, ymin=q25, ymax=q75, color=grp_r),
                   position = position_dodge2(width = 0.8),
                   linewidth=0.5) +
    geom_point(data = data, aes(x=poi_type, y=q50, color=grp_r),
               position = position_dodge2(width = 0.8),
               shape = 21, fill = "white", size = 2) +
    scale_color_manual(name = 'Group',
                       breaks=c('D', 'F'),
                       values=c('#7f88af', '#af887f')) +
    ylim(y.lm[1], y.lm[2]) +
    labs(x = 'POI type', y = y.lab)
  return(g + coord_flip())
}
g0 <- plot.poi(data = df.poi)
g0

# ---- ICE values by POI type share group (7 POI types, 4 quantile groups each)

plot.range.poi <- function(data, var, var.name, ice2plot, ice.cols,
                       y.lab='Nativity segregation', y.lm=c(-1, 1)){
  df2plot <- df2plot[df2plot$var %in% ice2plot, ]
  g <- ggplot() +
    theme_classic() +
    geom_linerange(data = df2plot, aes(x=poi_var_level, ymin=q25, ymax=q75, color=var),
                   position = position_dodge2(width = 0.8),
                   linewidth=0.5) +
    geom_point(data = df2plot, aes(x=poi_var_level, y=q50, color=var),
               position = position_dodge2(width = 0.8),
               shape = 21, fill = "white", size = 2) +
    geom_hline(yintercept = 0, color='#1e272e', linewidth=0.2, linetype = "longdash") +
    scale_color_manual(name = 'Type',
                       breaks=ice2plot,
                       values=ice.cols) +
    ylim(y.lm[1], y.lm[2]) +
    labs(x = var.name, y = y.lab) +
    facet_grid(grp_r~.)
  return(g + coord_flip())
}


cols <- c('#808e9b', '#3c40c6', '#0fbcf9', '#f53b57', '#ffa801')
ice2plot <- ice.names[1:5]
g1 <- plot.range.poi(data=df.seg, var='poi_e', var.name = 'Education',
                     ice2plot = ice2plot, ice.cols=cols)
g2 <- plot.range.poi(data=df.seg, var='poi_hw', var.name = 'Health and Wellness',
                     ice2plot = ice2plot, ice.cols=cols)
g3 <- plot.range.poi(data=df.seg, var='poi_fdg', var.name = 'Food, Drink, and Groceries',
                     ice2plot = ice2plot, ice.cols=cols)
g4 <- plot.range.poi(data=df.seg, var='poi_rt', var.name = 'Retail',
                     ice2plot = ice2plot, ice.cols=cols)
g5 <- plot.range.poi(data=df.seg, var='poi_rc', var.name = 'Recreation',
                     ice2plot = ice2plot, ice.cols=cols)
g6 <- plot.range.poi(data=df.seg, var='poi_m', var.name = 'Mobility',
                     ice2plot = ice2plot, ice.cols=cols)
g7 <- plot.range.poi(data=df.seg, var='poi_o', var.name = 'Other',
                     ice2plot = ice2plot, ice.cols=cols)

cols.d <- c('#f53b57', '#ffa801')
ice2plot.d <- ice.names[6:7]
g8 <- plot.range.poi(data=df.seg, var='poi_e', var.name = 'Education',
                     ice2plot = ice2plot.d, ice.cols=cols.d)
g9 <- plot.range.poi(data=df.seg, var='poi_hw', var.name = 'Health and Wellness',
                     ice2plot = ice2plot.d, ice.cols=cols.d)
g10 <- plot.range.poi(data=df.seg, var='poi_fdg', var.name = 'Food, Drink, and Groceries',
                     ice2plot = ice2plot.d, ice.cols=cols.d)
g11 <- plot.range.poi(data=df.seg, var='poi_rt', var.name = 'Retail',
                     ice2plot = ice2plot.d, ice.cols=cols.d)
g12 <- plot.range.poi(data=df.seg, var='poi_rc', var.name = 'Recreation',
                     ice2plot = ice2plot.d, ice.cols=cols.d)
g13 <- plot.range.poi(data=df.seg, var='poi_m', var.name = 'Mobility',
                     ice2plot = ice2plot.d, ice.cols=cols.d)
g14 <- plot.range.poi(data=df.seg, var='poi_o', var.name = 'Other',
                     ice2plot = ice2plot.d, ice.cols=cols.d)

# --- POI clusters ----
# 'Students' , 'Regular travelers', 'Recreation enthusiasts', 'Foodies', 'Wellness seekers', 'Navigators', 'Shoppers'
plot.range.poi.grp <- function(data, var, var.name, ice2plot, ice.cols,
                       y.lab='Nativity segregation', y.lm=c(-1, 1)){
  df2plot <- data[data$var %in% ice2plot, ]
  g <- ggplot() +
    theme_classic() +
    geom_linerange(data = df2plot, aes(x=poi_grp_name, ymin=q25, ymax=q75, color=var),
                   position = position_dodge2(width = 0.8),
                   linewidth=0.5) +
    geom_point(data = df2plot, aes(x=poi_grp_name, y=q50, color=var),
               position = position_dodge2(width = 0.8),
               shape = 21, fill = "white", size = 2) +
    geom_hline(yintercept = 0, color='#1e272e', linewidth=0.2, linetype = "longdash") +
    scale_color_manual(name = 'Type',
                       breaks=ice2plot,
                       values=ice.cols) +
    ylim(y.lm[1], y.lm[2]) +
    labs(x = var.name, y = y.lab) +
    facet_grid(grp_r~.)
  return(g + coord_flip())
}

cols <- c('#808e9b', '#3c40c6', '#0fbcf9', '#f53b57', '#ffa801')
ice2plot <- ice.names[1:5]
g15 <- plot.range.poi.grp(data=df.poi.grp.seg, var='poi_grp_name', var.name = 'POI lifestyle',
                     ice2plot = ice2plot, ice.cols=cols)

cols.d <- c('#f53b57', '#ffa801')
ice2plot.d <- ice.names[6:7]
g16 <- plot.range.poi.grp(data=df.poi.grp.seg, var='poi_grp_name', var.name = 'POI lifestyle',
                     ice2plot = ice2plot.d, ice.cols=cols.d)

# ---- Save figures / Segregation metrics
ggsave(filename = "figures/poi_type_shares.png", plot=g0,
       width = 5, height = 5, unit = "in", dpi = 300)

G1 <- ggarrange(g1, g2, g3, g4, g5, g6, g7, ncol = 4, nrow = 2,
               labels = c('a', 'b', 'c', 'd', 'e', 'f', 'g'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_disp_poi_type1.png", plot=G1,
       width = 15, height = 10, unit = "in", dpi = 300)

G2 <- ggarrange(g8, g9, g10, g11, g12, g13, g14, ncol = 4, nrow = 2,
               labels = c('a', 'b', 'c', 'd', 'e', 'f', 'g'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_disp_poi_type2.png", plot=G2,
       width = 15, height = 10, unit = "in", dpi = 300)

G3 <- ggarrange(g15, g16, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_disp_poi_type2.png", plot=G3,
       width = 10, height = 5, unit = "in", dpi = 300)