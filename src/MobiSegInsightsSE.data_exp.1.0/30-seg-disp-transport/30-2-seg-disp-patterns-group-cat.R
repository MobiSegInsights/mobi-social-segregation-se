# Title     : Range plots of nativity segregation change patterns
# Objective : Disparity vs. transit, car access including the statistical test (by clusters/groups)
# Created by: Yuan Liao
# Created on: 2023-07-25

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
df <- df[(df$focus=='no') & (df$ctrl_grp != 'None'), ]
df.tst <- as.data.frame(read_parquet('results/transport_association/stats_test_ctrl_grp.parquet'))

df$seg_r <- factor(df$seg_r, levels = c("D", "F"))
df.tst$seg_r <- factor(df.tst$seg_r, levels = c("D", "F"))
df$region_cat2 <- factor(df$region_cat2, levels = c("Urban", "Rural/Suburban"))
df.tst$region_cat2 <- factor(df.tst$region_cat2, levels = c("Urban", "Rural/Suburban"))
df$seg_r_grp <- interaction(df$seg_r, df$ctrl_grp)
df.tst$seg_r_grp <- interaction(df.tst$seg_r, df.tst$ctrl_grp)
df$seg_r_grp <- factor(df$seg_r_grp, levels = c("D.0", "F.0",
                                                "D.1", "F.1",
                                                "D.2", "F.2"),
labels = c("ProsperDrive (D)", "ProsperDrive (F)",
           "ThriftyMove (D)", "ThriftyMove (F)",
           "EliteWander (D)", "EliteWander (F)"))
df.tst$seg_r_grp <- factor(df.tst$seg_r_grp, levels = c("D.0", "F.0",
                                                        "D.1", "F.1",
                                                        "D.2", "F.2"),
labels = c("ProsperDrive (D)", "ProsperDrive (F)",
           "ThriftyMove (D)", "ThriftyMove (F)",
           "EliteWander (D)", "EliteWander (F)"))

plot.range <- function(var, data.stats, data, var.name, xlb, strp=F, y.log=F){
  df2plot <- data[data$var==var,]
  df.tst2plot <- data.stats[data.stats$var==var, ]
  df.tst2plot <- df.tst2plot[df.tst2plot$sig=='*', ]
  g <- ggplot() +
    theme_light() +
    geom_linerange(data = df2plot, aes(x=seg_r_grp, ymin=q25, ymax=q75, color=seg_change),
                   position = position_dodge2(width = 0.8),
                   linewidth=0.5) +
    geom_point(data = df2plot, aes(x=seg_r_grp, y=q50, color=seg_change),
               position = position_dodge2(width = 0.8),
               shape = 21, fill = "white", size = 2) +
    scale_color_manual(name = 'Change direction', values = c('darkblue', 'darkred')) +
    labs(x = xlb, y = var.name, title="Cohen's d (p<0.001)") +
    geom_text(data=df.tst2plot, aes(x=seg_r_grp, y = max(df2plot$q75)*1.05,
                                    label=round(cohen_d, digits = 2)),
           color = "black", show.legend = FALSE) +
    facet_grid(region_cat2~.)
  if (y.log) {
    g <- g +
      scale_y_log10()
  }
  if (strp) {
    g <- g +
      theme(legend.position = 'bottom', legend.key.height= unit(0.3, 'cm'),
      plot.margin = margin(1,0.5,0,0, "cm"),
      plot.title = element_text(hjust = 1, size=10),
      strip.text.x = element_blank())
  } else {
    g <- g +
      theme(legend.position = 'bottom', legend.key.height= unit(0.3, 'cm'),
      plot.margin = margin(1,0.5,0,0, "cm"),
      plot.title = element_text(hjust = 1, size=10))
  }
  return(g + coord_flip())
}

g1 <- plot.range(var='cum_jobs', data.stats = df.tst, data=df,
                 var.name='Car accessibility to jobs', xlb="Nativity segregation change", strp=T, y.log=T)
g2 <- plot.range(var='cum_stops', data.stats = df.tst, data=df,
                 var.name='Access to transit stops', xlb="")
G <- ggarrange(g1, g2, common.legend = T)
# ggsave(filename = "figures/seg_disp_ice_car.png", plot=g1, width = 5, height = 12, unit = "in", dpi = 300)
# ggsave(filename = "figures/seg_disp_ice_transit.png", plot=g2, width = 5, height = 12, unit = "in", dpi = 300)
ggsave(filename = "figures/seg_disp_ice.png", plot=G, width = 15, height = 10, unit = "in", dpi = 300)
