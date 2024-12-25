import numpy as np
import torch


class ImageAutotone:

	@classmethod
	def INPUT_TYPES(s):
		return {
		    "required": {
		        "image": ("IMAGE", ),
		        "shadows": ("STRING", {
		            "default": "0,0,0",
		            "tooltip": "The color to use for the shadows in the image. This should be a comma-separated RGB value (e.g., '0,0,0' for black) or HEX string (e.g. '#000000')."
		        }),
		        "highlights": ("STRING", {
		            "default": "255,255,255",
		            "tooltip": "The color to use for the highlights in the image. This should be a comma-separated RGB value (e.g., '255,255,255' for white) or HEX string (e.g. '#FFFFFF')."
		        }),
		        "shadow_clip": ("FLOAT", {
		            "default": 0.001,
		            "min": 0.0,
		            "max": 1.0,
		            "step": 0.001,
		            "tooltip": "The percentage of pixels to clip from the shadows. This is a value between 0 and 1."
		        }),
		        "highlight_clip": ("FLOAT", {
		            "default": 0.001,
		            "min": 0.0,
		            "max": 1.0,
		            "step": 0.001,
		            "tooltip": "The percentage of pixels to clip from the highlights. This is a value between 0 and 1."
		        }),
		    }
		}

	RETURN_TYPES = ("IMAGE", )
	FUNCTION = "op"
	CATEGORY = "image"
	DESCRIPTION = """Clip color channels independently to increase contrast and alter color cast. This is a reinterpretation of Photoshop's "Auto Tone" algorithm."""

	# Thank you to Gerald Bakker for the following writeup on the algorithm:
	# https://geraldbakker.nl/psnumbers/auto-options.html

	def op(self, image, highlights, shadows, shadow_clip, highlight_clip):

		def str_to_rgb(color_string):
			"""Converts a color string to a tuple of RGB values"""
			if color_string[0].isdigit():
				return tuple(map(int, color_string.split(",")))
			elif color_string.startswith("#"):
				return bytes.fromhex(color_string[1:])

		def calculate_adjustment_values(hist, total_pixels, clip_percent):
			clip_threshold = total_pixels * clip_percent
			cumulative_hist = hist.cumsum()

			# Find the first and last indices where the cumulative histogram exceeds the clip thresholds
			lower_bound_idx = np.where(cumulative_hist > clip_threshold)[0][0]
			upper_bound_idx = np.where(cumulative_hist < (total_pixels - clip_threshold))[0][-1]

			return lower_bound_idx, upper_bound_idx

		shadows = np.array(str_to_rgb(shadows))
		# midtones are only used in other algorithms
		# midtones = str_to_rgb(self.Unprompted.parse_arg("midtones", "128,128,128"))
		highlights = np.array(str_to_rgb(highlights))

		total_images = image.shape[0]
		out_images = []

		for i in range(total_images):
			# image is a 4d tensor array in the format of [B, H, W, C]
			img_array = 255. * image[i].cpu().numpy()
			# img_array = np.clip(this_img, 0, 255).astype(np.uint8)

			# Process each channel (R, G, B) separately
			for channel in range(3):
				# Calculate the histogram of the current channel
				hist, _ = np.histogram(img_array[:, :, channel].flatten(), bins=256, range=[0, 255])

				# Total number of pixels
				total_pixels = img_array.shape[0] * img_array.shape[1]

				# Calculate the adjustment values based on clipping percentages
				dark_value, light_value = calculate_adjustment_values(hist, total_pixels, shadow_clip)
				_, upper_light_value = calculate_adjustment_values(hist, total_pixels, highlight_clip)

				# Adjust light_value using upper_light_value for highlights
				light_value = max(light_value, upper_light_value)

				# Avoid division by zero
				if light_value == dark_value:
					continue

				# Scale and clip the channel values
				img_array[:, :, channel] = (img_array[:, :, channel] - dark_value) * (highlights[channel] - shadows[channel]) / (light_value - dark_value) + shadows[channel]
				img_array[:, :, channel] = np.clip(img_array[:, :, channel], 0, 255)

			img_array = np.clip(img_array, 0, 255).astype(np.uint8)
			image = Image.fromarray(img_array)

			out_images.append(img_array)

		restored_img_np = np.array(out_images).astype(np.float32) / 255.0
		restored_img_tensor = torch.from_numpy(restored_img_np)

		return (restored_img_tensor, )


NODE_CLASS_MAPPINGS = {
    "ImageAutotone": ImageAutotone,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageAutotone": "Image Autotone",
}
