# Title     : POI share by type and group
# Objective : Justify small differences between F and N
# Created by: Yuan Liao
# Created on: 2024-05-09

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

rename_dict <- c(
  D = "N",
  N = "M"
)
df <- as.data.frame(read_parquet('results/poi_share_range_by_group.parquet')) %>%
  mutate(grp_r = recode(grp_r, !!!rename_dict)) %>%
  mutate(lower = ave-std) %>%
  mutate(upper = ave+std)
df <- arrange(df, grp_r, ave)
lbs <- unique(df$poi_type)
df$poi_type <- factor(df$poi_type, levels = lbs, labels = lbs)

df.t <- as.data.frame(read_parquet('results/poi_share_by_group.parquet')) %>%
  mutate(grp_r = recode(grp_r, !!!rename_dict))

cols <- c('N'='#001260', 'F'='#601200', 'M'='gray75')

g1 <- ggplot(data = df, aes(y=poi_type, color=grp_r)) +
  theme_hc() +
  geom_errorbarh(aes(xmin=lower, xmax=upper), height = .02, size=1, alpha=0.3,
                 position = position_dodge(width = 0.8)) +
  geom_point(aes(x=ave), shape = 21, fill = "white", size = 2,
             position = position_dodge(width = 0.8)) +
  labs(y = 'POI type',
       x = 'Share of activity time outside home') +
  scale_color_manual(name = "Birth background group",
                     values = cols) +
  scale_fill_manual(name = "Birth background group",
                   values = cols) +
  theme(legend.position="bottom", strip.background = element_blank())

g2 <- ggplot(df.t, aes(fill=poi_type, x=visit_share, y=grp_r)) +
  theme_hc() +
  geom_bar(position="stack", stat="identity", width = 0.5, color='white') +
  labs(x = 'Share of visits (%)',
       y = 'Birth background group') +
  scale_fill_npg(name = "POI type") +
  theme(legend.position="bottom", strip.background = element_blank())

G <- ggarrange(g2, g1, ncol = 2, nrow = 1, labels = c('a', 'b'), widths = c(1.4, 1))
ggsave(filename = "figures/panels/fig_b1.png", plot=G,
       width = 12, height = 6, unit = "in", dpi = 300, bg = 'white')