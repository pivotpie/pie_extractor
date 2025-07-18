"""Create a simple test image for testing vision models."""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image():
    """Create a simple test image with some text and shapes."""
    # Create a new image with white background
    width, height = 400, 300
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Draw a rectangle
    draw.rectangle([50, 50, 350, 250], outline='blue', width=2)
    
    # Add some text
    try:
        # Try to use a common font
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        # Fall back to default font if Arial is not available
        font = ImageFont.load_default()
    
    draw.text((100, 100), "Test Image for Vision Model", fill='black', font=font)
    draw.text((100, 130), "This is a test image for vision model fallback testing.", fill='black', font=font)
    
    # Save the image
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    image_path = os.path.join(os.path.dirname(__file__), "test_image.png")
    image.save(image_path)
    print(f"Test image created at: {image_path}")
    return image_path

if __name__ == "__main__":
    create_test_image()
