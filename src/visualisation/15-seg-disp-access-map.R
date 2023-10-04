# Title     : Transport access vs. experienced nativity segregation
# Objective : On the map of central Gothenburg
# Created by: Yuan Liao
# Created on: 2023-10-02

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(ggmap)
library(ggspatial)
library(sf)
library(sp)
library(scico)
library(spdep)
library(ggraph)
library(arrow)
library(scales)
library(ggExtra)
library(RColorBrewer)
library(yaml)
library(mapdeck)
library(htmlwidgets)
library(purrr)
library(webshot2)
library(magick)
options(scipen=10000)
# addalpha()
addalpha <- function(colors, alpha=1.0) {
  r <- col2rgb(colors, alpha=T)
  # Apply alpha
  r[4,] <- alpha*255
  r <- r/255.0
  return(rgb(r[1,], r[2,], r[3,], r[4,]))
}


#------------ Experienced vs. residential --------------
gdf <- st_read('results/seg_disp_access_map.geojson')
gdf <- gdf %>%
  filter(region_cat2 == 'Urban')


# --- Access on the map ---
keys_manager <- read_yaml('dbs/keys.yaml')

# Define the breaks and colors for ICE_e
breaks <- c(-1, -0.6, -0.2, 0, 0.2, 0.6, 1)
custom_palette <- colorRampPalette(c("firebrick1", "white", "dodgerblue1"))(length(breaks) - 1)
custom_palette <- addalpha(custom_palette, 0.5)
custom_palette.leg <- colorRampPalette(c("firebrick1", "white", "dodgerblue1"))(length(breaks))
custom_palette.leg <- addalpha(custom_palette.leg, 0.5)

gdf$ice_e_col <- cut(gdf$ICE_e, breaks = breaks, labels = custom_palette, include.lowest = TRUE)

## create a manual legend
legend <- mapdeck::legend_element(
  variables = breaks
  , colours = custom_palette.leg
  , colour_type = "fill"
  , variable_type = 'gradient'
  , title = 'ICEe'
)
js_legend.ice_e <- mapdeck::mapdeck_legend(legend)

# Define the breaks and colors for transit
breaks <- c(0, 1, 10, 100, 1000, 10000, 100000, 210000)

# Create a palette based on the "plasma" color map
plasma_palette <- viridis_pal(option = "plasma")(length(breaks) - 1)
# Generate a list of colors
custom_palette <- colorRampPalette(plasma_palette)(length(breaks) - 1)
custom_palette <- addalpha(custom_palette, 0.5)
plasma_palette.leg <- viridis_pal(option = "plasma")(length(breaks))
custom_palette.leg <- colorRampPalette(plasma_palette.leg)(length(breaks))
custom_palette.leg <- addalpha(custom_palette.leg, 0.5)

gdf$Access_transit_col <- cut(gdf$Access_transit, breaks = breaks, labels = custom_palette, include.lowest = TRUE)

## create a manual legend
legend <- mapdeck::legend_element(
  variables = breaks
  , colours = custom_palette.leg
  , colour_type = "fill"
  , variable_type = 'gradient'
  , title = "Access by transit"
)
js_legend.access_transit <- mapdeck::mapdeck_legend(legend)

# Define the breaks and colors for car
breaks <- c(100, 10000, 20000, 40000, 250000, 300000, 350000)

# Create a palette based on the "plasma" color map
plasma_palette <- viridis_pal(option = "plasma")(length(breaks) - 1)
# Generate a list of colors
custom_palette <- colorRampPalette(plasma_palette)(length(breaks) - 1)
custom_palette <- addalpha(custom_palette, 0.5)
plasma_palette.leg <- viridis_pal(option = "plasma")(length(breaks))
custom_palette.leg <- colorRampPalette(plasma_palette.leg)(length(breaks))
custom_palette.leg <- addalpha(custom_palette.leg, 0.5)

gdf$Access_car_col <- cut(gdf$Access_car, breaks = breaks, labels = custom_palette, include.lowest = TRUE)

## create a manual legend
legend <- mapdeck::legend_element(
  variables = breaks
  , colours = custom_palette.leg
  , colour_type = "fill"
  , variable_type = 'gradient'
  , title = "Access by car"
)
js_legend.access_car <- mapdeck::mapdeck_legend(legend)

#---- Define the function for ploting ----
plt.access <- function(geo=gdf, png='tst', col='ICE_e', legend=lgd, zoom=11) {
  file.url <- paste0(getwd(), "/figures/tst.html")
  file.png <- paste0(getwd(), "/figures/", png, '.png')
  ms <- mapdeck_style("dark")
  mapdeck(token=keys_manager$maps$mapdeck,
          style = ms, pitch = 45, zoom = 14) %>%
              add_polygon(
                  data = geo
                  , layer_id = 'seg'
                  , fill_colour = col
                  , legend = legend
                  , fill_opacity = 150
                  , elevation = "pop"
                  , update_view = FALSE
                  , focus_layer = FALSE
              )%>%
    mapdeck_view(
      location = c(11.974560, 57.708870),
      zoom = zoom,
      pitch = 45
    ) %>% saveWidget(file.url)

  webshot(url=file.url,
          file=file.png,
          delay = 5,
          vwidth = 900,
          vheight = 900
  )
}
plt.access(geo=gdf, png='a_ice_e', col='ice_e_col', legend=js_legend.ice_e, zoom=10)
plt.access(geo=gdf, png='a_access_pt', col='Access_transit_col', legend=js_legend.access_transit, zoom=10)
plt.access(geo=gdf, png='a_access_car', col='Access_car_col', legend=js_legend.access_car, zoom=10)

# ----- Add labels to produced webshot images -----------
add.label <- function(file="figures/a_access_car.png", label='(a)'){
  # Load the captured image
  image <- image_read(file)
  # Define the width of the space between the images (in pixels)
  space_height <- 50
  # Get the dimensions (width and height) of image1
  image.info <- image_info(image)
  image_width <- image.info$width

  # Create a blank space image
  blank_space <- image_blank(image_width, space_height, color = "white")
  combined_image <- image_append(c(blank_space, image), stack = TRUE)

  # Add a title using magick functions
  image_with_title <- combined_image %>%
    image_annotate(label, gravity = "northwest",
                   color = "black", size = 40)

  # Save the modified image
  image_write(image_with_title, file) #

}
add.label(file="figures/a_access_car.png", label='(a)')
add.label(file="figures/a_access_pt.png", label='(b)')
add.label(file="figures/a_ice_e.png", label='(c)')

# ----- Combine labeled images -------
# Load the two input .png images
image1 <- image_read("figures/a_access_car.png")
image2 <- image_read("figures/a_access_pt.png")
image3 <- image_read("figures/a_ice_e.png")
# Define the width of the space between the images (in pixels)
space_width <- 30
# Get the dimensions (width and height) of image1
image1_info <- image_info(image1)
image1_width <- image1_info$width
image1_height <- image1_info$height

# Create a blank space image
blank_space <- image_blank(space_width, image1_height, color = "white")

# Combine the images horizontally (side by side)
combined_image <- image_append(c(image1, blank_space, image2, blank_space, image3), stack = FALSE)
#combined <- image_append(image_scale(c(combined_image, image_read("figures/seg_disp_access_all.png")),
#                                    "3000"), stack = TRUE)
# Save the combined image as a new .png file
image_write(combined_image, "figures/a_access_ice_combined.png")