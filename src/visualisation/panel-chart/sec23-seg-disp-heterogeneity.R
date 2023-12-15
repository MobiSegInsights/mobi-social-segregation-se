# Title     : Range plots of nativity segregation change patterns (e, e1, e2, enh)
# Objective : Disparity vs. region, car ownership, income, mobility range, car access, transit access
# Created by: Yuan Liao
# Created on: 2023-12-8

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(magick)
options(scipen=10000)

df <- as.data.frame(read_parquet('results/seg_sims_range_by_group.parquet'))
ice.names <- c('Residential', 'Experienced', 'Experienced (outside home)',
               'Homophily simulated (outside home)', 'Limited-travel simulated (outside home)',
               'Homophily effect', 'Limited-travel effect')
ac_car <- c('2154', '5769', '8759', '11430', '14795',
            '18815', '23451', '28767', '33761', '37591',
            '42247', '47249', '57486', '71773', '94654',
            '197860', '240514', '312917', '435769', '729616',
            '835347', '862407', '874743', '900815', '923811')
ac_pt <- c('6', '40', '152', '361', '641',
           '993', '1391', '1953', '2597', '3334',
           '4218', '5426', '6806', '8585', '11088',
           '13780', '17174', '21364', '26624', '39710',
           '65814', '111495', '234249', '329749', '414057')
df <- df %>%
  filter(grp_r!='N')
df$grp_r <- factor(df$grp_r, levels = c("D", "F"))
df$var <- factor(df$var, levels = c("ice_r", "ice_e", "ice_enh", "ice_e1", "ice_e2",
                                    'delta_ice1', 'delta_ice2'),
                 labels = ice.names)

plot.range <- function(data, var, var.name, ice2plot, ice.cols,
                       y.lab='Nativity segregation', y.lm=c(-1, 1)){
  df2plot <- data[data$cate_name==var,]
  df2plot <- df2plot[df2plot$var %in% ice2plot, ]
  if (var %in% c('car_cat', 'low_inc_cat')) {
    df2plot$cate_level <- factor(df2plot$cate_level, levels = c("L", "M", "H"))
  }
  if (var == 'access_car') {
    df2plot$cate_level <- factor(df2plot$cate_level, levels = ac_car,
                                 labels = seq(1,25,1))
  }
  if (var == 'access_pt') {
    df2plot$cate_level <- factor(df2plot$cate_level, levels = ac_pt,
                                 labels = seq(1,25,1))
  }
  g <- ggplot() +
    theme_classic() +
    geom_linerange(data = df2plot, aes(x=cate_level, ymin=q25, ymax=q75, color=var),
                   position = position_dodge2(width = 0.8),
                   linewidth=0.5) +
    geom_point(data = df2plot, aes(x=cate_level, y=q50, color=var),
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
g1 <- plot.range(data=df, var='region_cat', var.name = 'Region type',
                 ice2plot = ice2plot, ice.cols=cols)
g2 <- plot.range(data=df, var='car_cat', var.name = 'Car ownership',
                 ice2plot = ice2plot, ice.cols=cols)
g3 <- plot.range(data=df, var='low_inc_cat', var.name = 'Income',
                 ice2plot = ice2plot, ice.cols=cols)
g4 <- plot.range(data=df, var='mobi_range_cat', var.name = 'Mobility range',
                 ice2plot = ice2plot, ice.cols=cols)
g5 <- plot.range(data=df, var='access_car', var.name = 'Car access to jobs',
                 ice2plot = ice2plot, ice.cols=cols)
g6 <- plot.range(data=df, var='access_pt', var.name = 'Transit access to jobs',
                 ice2plot = ice2plot, ice.cols=cols)

cols.d <- c('#f53b57', '#ffa801')
ice2plot.d <- ice.names[6:7]
g7 <- plot.range(data=df, var='region_cat', var.name = 'Region type',
                 ice2plot = ice2plot.d, ice.cols=cols.d,
                 y.lab='Reduced nativity segregation', y.lm=c(-0.5, 0.1))

g8 <- plot.range(data=df, var='car_cat', var.name = 'Car ownership',
                 ice2plot = ice2plot.d, ice.cols=cols.d,
                 y.lab='Reduced nativity segregation', y.lm=c(-0.5, 0.1))

g9 <- plot.range(data=df, var='low_inc_cat', var.name = 'Income',
                 ice2plot = ice2plot.d, ice.cols=cols.d,
                 y.lab='Reduced nativity segregation', y.lm=c(-0.5, 0.1))

g10 <- plot.range(data=df, var='mobi_range_cat', var.name = 'Mobility range',
                 ice2plot = ice2plot.d, ice.cols=cols.d,
                  y.lab='Reduced nativity segregation', y.lm=c(-0.5, 0.1))

g11 <- plot.range(data=df, var='access_car', var.name = 'Car access to jobs',
                 ice2plot = ice2plot.d, ice.cols=cols.d,
                  y.lab='Reduced nativity segregation', y.lm=c(-0.5, 0.1))

g12 <- plot.range(data=df, var='access_pt', var.name = 'Transit access to jobs',
                 ice2plot = ice2plot.d, ice.cols=cols.d,
                  y.lab='Reduced nativity segregation', y.lm=c(-0.5, 0.1))


# ---- Save figures / Segregation metrics
G1 <- ggarrange(g1, g2, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_disp_region_car.png", plot=G1,
       width = 10, height = 5, unit = "in", dpi = 300)

G2 <- ggarrange(g3, g4, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_disp_inc_mobi.png", plot=G2,
       width = 10, height = 5, unit = "in", dpi = 300)

G3 <- ggarrange(g5, g6, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_disp_access.png", plot=G3,
       width = 10, height = 8, unit = "in", dpi = 300)

# ---- Save figures / Deltas of simulations (outside home)
G4 <- ggarrange(g7, g8, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_delta_sim_region_car.png", plot=G4,
       width = 10, height = 5, unit = "in", dpi = 300)

G5 <- ggarrange(g9, g10, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_delta_sim_inc_mobi.png", plot=G5,
       width = 10, height = 5, unit = "in", dpi = 300)

G6 <- ggarrange(g11, g12, ncol = 2, nrow = 1,
               labels = c('a', 'b'), common.legend = T, legend="bottom",
               font.label = list(face = "bold"))
ggsave(filename = "figures/seg_delta_sim_access.png", plot=G6,
       width = 10, height = 8, unit = "in", dpi = 300)

# ----- Combine labeled images -------
# Load the two input .png images
image1 <- image_read("figures/seg_disp_FD_sim1.png")
image2 <- image_read("figures/seg_disp_FD_sim2.png")

# Get the dimensions (width and height) of image1
image1_width <- image_info(image1)$width

# Create a blank space image
blank_space_w <- image_blank(3, image1_width, color = "white")

# Combine the images horizontally (side by side)
combined_image <- image_append(c(image1, blank_space_w, image2), stack = F)
image_write(combined_image, "figures/seg_disp_FD_sims.png")