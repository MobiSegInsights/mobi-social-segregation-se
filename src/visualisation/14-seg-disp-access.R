# Title     : Share of reduced ICE vs. access group
# Objective : Share of reduced ICE vs. access group
# Created by: Yuan Liao
# Created on: 2023-9-26

library(ggplot2)
library(ggpubr)
library(scico)
library(dplyr)
library(arrow)
library(scales)
library(ggExtra)
library(ggthemes)
options(scipen=10000)

#------------ Share of decreased vs. access --------------
fake_scico <- scico(3, palette = "vik")
df.ice <- as.data.frame(read_parquet('results/seg_disp_access.parquet'))

df.ice2plot.D <- df.ice %>%
  filter(ice_birth_resi_cat=='D') %>%
  filter(region_cat2 == 'Urban')
g1 <- ggplot(data=df.ice2plot.D, aes(x=access, y=share_dec)) +
  geom_point(color=fake_scico[1]) +
  geom_smooth(color=fake_scico[1], level = 0.95) +
  scale_x_continuous(trans='log10') +
  ylim(90, 100) +
  labs(x='Access to jobs in 30 min', y='Share of individuals with > 20% reduced segregation') +
  facet_grid(.~mode, scales = "free_x") +
  theme_hc()

df.ice2plot.F <- df.ice %>%
  filter(ice_birth_resi_cat=='F') %>%
  filter(region_cat2 == 'Urban')
g2 <- ggplot(data=df.ice2plot.F, aes(x=access, y=share_dec)) +
  geom_point(color=fake_scico[3]) +
  geom_smooth(color=fake_scico[3], level = 0.95) +
  scale_x_continuous(trans='log10') +
  ylim(0, 100) +
  labs(x='Access to jobs in 30 min', y='Share of individuals with > 20% reduced segregation') +
  facet_grid(.~mode, scales = "free_x") +
  theme_hc()

G <- ggarrange(g1, g2, ncol = 2, nrow = 1,
               labels = c('(a)', '(b)'))
ggsave(filename = "figures/seg_disp_access.png", plot=G,
       width = 14, height = 5, unit = "in", dpi = 300)

#-------ICE vs Access--------
df.ice.r <- as.data.frame(read_parquet('results/seg_disp_access_raw.parquet'))

df.icer2plot <- df.ice.r %>%
  filter(region_cat2 == 'Urban') %>%
  filter(var %in% c('ice_birth', 'ice_birth_resi'))
g3 <- ggplot(data=df.icer2plot, aes(x=access, y=q50, color=ice_birth_resi_cat, shape=var)) +
  geom_point() +
#  geom_linerange(aes(x=access, ymin=q25, ymax=q75, color=ice_birth_resi_cat),
#                   linewidth=0.5, show.legend = FALSE) +
  geom_smooth(level = 0.95) +
  scale_shape_manual(name = 'ICE', values=c(15, 4), labels = c('Experienced', 'Residential')) +
  scale_color_manual(name='Group', values=c(fake_scico[1], fake_scico[3])) +
  scale_x_continuous(trans='log10') +
  labs(x='Access to jobs in 30 min', y='Nativity segregation') +
  ylim(-0.5, 0.5) +
  facet_grid(.~mode, scales = "free_x") +
  theme_hc()

ggsave(filename = "figures/seg_disp_access_raw.png", plot=g3,
       width = 8, height = 5, unit = "in", dpi = 300)

G2 <- ggarrange(g3, g1, g2, ncol = 3, nrow = 1,
               labels = c('(a)', '(b)', '(c)'))
ggsave(filename = "figures/seg_disp_access_all.png", plot=G2,
       width = 15, height = 6, unit = "in", dpi = 300)