# Title     : Range plots of nativity segregation change patterns
# Objective : Disparity vs. income, transit, car access including the statistical test
# Created by: Yuan Liao
# Created on: 2023-7-06

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
options(scipen=10000)


# ------------- Data range visualization ---------------
df <- as.data.frame(read_parquet('results/transport_association/seg_disarity_patterns_stats.parquet'))
df.thr <- df[df$focus=='yes', ]
df <- df[df$focus=='no', ]
df.tst <- as.data.frame(read_parquet('results/transport_association/stats_test.parquet'))

df$seg_cross <- factor(df$seg_cross, levels = c("DD", "FF", "DF", "FD"))
df.tst$seg_cross <- factor(df.tst$seg_cross, levels = c("DD", "FF", "DF", "FD"))

plot.range <- function(var, data, data.stats, var.name, y.log=F){
  df2plot <- data[data$var==var,]
  df.tst2plot <- data.stats[(data.stats$var==var) & (data.stats$sig=='*'),]
  g <- ggplot() +
    theme_minimal() +
    geom_linerange(data = df2plot, aes(x=seg_cross, ymin=q25, ymax=q75, color=seg_change),
                   position = position_dodge2(width = 0.8),
                   linewidth=0.5) +
    geom_point(data = df2plot, aes(x=seg_cross, y=q50, color=seg_change),
               position = position_dodge2(width = 0.8),
               shape = 21, fill = "white", size = 2) +
    geom_point(data=df.tst2plot, aes(x=seg_cross, y = max(df2plot$q75)*1.05),
               color = "black", size = 5, shape='*') +
    scale_color_manual(name = 'Change direction', values = c('gray25', 'darkblue', 'darkred')) +
    labs(x = "Nativity segregation change (V - R)", y = var.name) +
    facet_grid(.~region_cat) +
    theme(legend.position = 'bottom', legend.key.height= unit(0.3, 'cm'),
          plot.margin = margin(1,0.5,0,0, "cm"))
  if (y.log) {
    g <- g +
      scale_y_log10()
  }
  return(g)
}

g1 <- plot.range(var='Lowest income group', data=df, data.stats = df.tst, var.name='Lowest income group')
g2 <- plot.range(var='car_ownership', data=df, data.stats = df.tst, var.name='Car ownership (/capita)')
g3 <- plot.range(var='cum_jobs', data=df, data.stats = df.tst, var.name='Car accessibility to jobs', y.log=T)
g4 <- plot.range(var='cum_stops', data=df, data.stats = df.tst, var.name='Access to transit stops')

ggsave(filename = "figures/seg_disp_ice_income.png", plot=g1, width = 10, height = 4, unit = "in", dpi = 300)
ggsave(filename = "figures/seg_disp_ice_car_o.png", plot=g2, width = 10, height = 4, unit = "in", dpi = 300)
ggsave(filename = "figures/seg_disp_ice_car_a.png", plot=g3, width = 10, height = 4, unit = "in", dpi = 300)
ggsave(filename = "figures/seg_disp_ice_pt_a.png", plot=g4, width = 10, height = 4, unit = "in", dpi = 300)

g5 <- plot.range(var='Lowest income group', data=df.thr, var.name='Lowest income group')
g6 <- plot.range(var='car_ownership', data=df.thr, var.name='Car ownership (/capita)')
g7 <- plot.range(var='cum_jobs', data=df.thr, var.name='Car accessibility to jobs', y.log=T)
g8 <- plot.range(var='cum_stops', data=df.thr, var.name='Access to transit stops', y.log=T)

ggsave(filename = "figures/seg_disp_ice_income_thr.png", plot=g5, width = 10, height = 5, unit = "in", dpi = 300)
ggsave(filename = "figures/seg_disp_ice_car_o_thr.png", plot=g6, width = 10, height = 5, unit = "in", dpi = 300)
ggsave(filename = "figures/seg_disp_ice_car_a_thr.png", plot=g7, width = 10, height = 5, unit = "in", dpi = 300)
ggsave(filename = "figures/seg_disp_ice_pt_a_thr.png", plot=g8, width = 10, height = 5, unit = "in", dpi = 300)

