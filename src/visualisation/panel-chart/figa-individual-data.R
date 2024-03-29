# Title     : Simulations and interactions
# Objective : Simulation results and interactions insights
# Created by: Yuan Liao
# Created on: 2024-03-28

library(dplyr)
library(ggplot2)
library(Hmisc)
library(ggsci)
library(ggbeeswarm)
library(cowplot)
library(ggridges)
library(ggthemes)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(hrbrthemes)
library(magick)

options(scipen=10000)

df <- as.data.frame(read_parquet('results/plot/seg_res_raw_plot.parquet'))
vars <- c('ice_r', 'ice_enh', 'ice_e1', 'ice_e2', 'radius_of_gyration', 'car_ownership', 'cum_jobs_pt')
rename_dict <- c(
  ice_r = "Residential",
  ice_enh = "Experienced",
  ice_e1 = "No-homophily",
  ice_e2 = "No-homophily \n& equalized mobility",
  radius_of_gyration = "Mobility range (km)",
  car_ownership = "Car ownership",
  cum_jobs_pt = "Job accessibility by transit"
)
df <- df %>%
  mutate(variable = recode(variable, !!!rename_dict))

vars2plot <- c('Residential', 'Experienced', 'No-homophily', 'No-homophily \n& equalized mobility')
g1 <- ggplot(data=df[df$variable %in% vars2plot,],
            aes(x=value, y = ..count../sum(..count..), weight=wt_p, color=variable)) +
  theme_hc() +
  geom_vline(aes(xintercept = 0), color='gray', linewidth=1) +
  geom_freqpoly(bins=30, linewidth=1, alpha=0.7) +
  scale_color_npg(name = "") +
  labs(y = 'Fraction of individuals',
       x = 'Nativity segregation level') +
  guides(color = guide_legend(ncol = 1)) +
  theme(legend.position = c(.8, .85),
        legend.background = element_blank())

g1
var <- 'Mobility range (km)'
g2 <- ggplot(data=df[df$variable == var,],
            aes(x=value, y = ..count../sum(..count..), weight=wt_p)) +
  theme_hc() +
  geom_freqpoly(bins=30, linewidth=1, alpha=0.7) +
  labs(y = 'Fraction of individuals',
       x = var) +
  scale_x_continuous(trans='log10')

var <- 'Car ownership'
g3 <- ggplot(data=df[df$variable == var,],
            aes(x=value, y = ..count../sum(..count..), weight=wt_p)) +
  theme_hc() +
  geom_freqpoly(bins=30, linewidth=1, alpha=0.7) +
  labs(y = 'Fraction of individuals',
       x = var)

var <- 'Job accessibility by transit'
g4 <- ggplot(data=df[df$variable == var,],
            aes(x=value, y = ..count../sum(..count..), weight=wt_p)) +
  theme_hc() +
  geom_freqpoly(bins=30, linewidth=1, alpha=0.7) +
  labs(y = 'Fraction of individuals',
       x = var) +
  scale_x_continuous(trans='log10')

G <- ggarrange(g1, g2, g3, g4, ncol = 2, nrow = 2,
               labels = c('a', 'b', 'c', 'd'))
ggsave(filename = "figures/panels/fig_a1.png", plot=G,
       width = 12, height = 8, unit = "in", dpi = 300, bg = 'white')